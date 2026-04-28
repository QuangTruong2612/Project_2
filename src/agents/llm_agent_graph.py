"""Multi-agent graph dùng native tool-calling (bind_tools + ToolNode style).

Kiến trúc:
    START -> agent_router (with_structured_output -> chọn next_agent)
                |
                +--> agent_expense  <-> tools_expense  -> END
                |
                +--> agent_weather  <-> tools_weather  -> END
                |
                +--> agent_news     <-> tools_news     -> END
                |
                +--> agent_main -> END

Lưu ý: Specialist sau khi xong vong tool sẽ tự sinh AIMessage cuối cùng
(dựa trên ToolMessage trong context) và đi thẳng đến END. `agent_main` chỉ
được dùng cho các yêu cầu không cần tool (chào hỏi, câu hỏi chung). Việc
bắt specialist đi qua agent_main dẫn tới việc agent_main rút gọn / viết đè
lên câu trả lời tốt của specialist — gây mất thông tin (vd: weather data bị
thay bằng câu follow-up rỗng).

Cốt lõi:
- Mỗi specialist `bind_tools(...)` tools tương ứng → LLM gọi tool qua native
  tool-calling thay vì tự sinh chuỗi `ACTION:` / `ARGUMENTS:`. Bỏ hoàn toàn
  việc parse text → loại bỏ một nguồn hallucination lớn.
- Router dùng `with_structured_output(RouteDecision)` để bắt LLM trả về 1
  trong 4 giá trị Literal hợp lệ.
- Tool node tự inject `user_id` từ state vào args (LLM không cần biết).
- State chỉ giữ `messages` làm source of truth (qua add_messages reducer);
  bỏ các trường `last_agent_response`/`tool_observations` của bản cũ vốn
  tích luỹ stale data qua nhiều turn và gây hallucination.
"""

from __future__ import annotations

from typing import Callable, List, Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.agents.llm_state import AgentState
from src.core import settings
from src.prompts.prompts import AGENT_PROFILE
from src.tools import (
    add_expense_tool,
    delete_expense_tool,
    get_expense_tool,
    get_news_url,
    get_weather_current_tool,
    get_weather_forecast_tool,
    update_expense_tool,
)

# ─── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",
    temperature=0.1,
)


# ─── Tool buckets cho từng agent ───────────────────────────────────────────────

EXPENSE_TOOLS = [
    add_expense_tool,
    get_expense_tool,
    update_expense_tool,
    delete_expense_tool,
]
WEATHER_TOOLS = [get_weather_current_tool, get_weather_forecast_tool]
NEWS_TOOLS = [get_news_url]

# Các tool cần `user_id` được inject tự động từ state (LLM không tự điền)
TOOLS_NEEDING_USER_ID = {
    "add_expense_tool",
    "get_expense_tool",
    "update_expense_tool",
    "delete_expense_tool",
}


# ─── Router (structured output) ────────────────────────────────────────────────

class RouteDecision(BaseModel):
    """Quyết định điều phối: chọn agent chuyên môn xử lý yêu cầu."""

    next_agent: Literal[
        "agent_expense", "agent_weather", "agent_news", "agent_main"
    ] = Field(
        description=(
            "Tên agent sẽ xử lý yêu cầu mới nhất của người dùng. "
            "Chọn 1 trong 4: agent_expense | agent_weather | agent_news | agent_main."
        )
    )


router_llm = llm.with_structured_output(RouteDecision)

def _system_for(agent_name: str) -> SystemMessage:
    profile = AGENT_PROFILE[agent_name]
    return SystemMessage(content=f"{profile['role']}\n{profile['system_instruction']}")


async def agent_router_node(state: AgentState) -> dict:
    """Phân loại intent của user và chọn agent kế tiếp."""
    messages: List[BaseMessage] = state.get("messages", [])
    routing_input: List[BaseMessage] = [_system_for("agent_router"), *messages]
    decision: RouteDecision = await router_llm.ainvoke(routing_input)
    return {"next_agent": decision.next_agent}


def route_after_router(state: AgentState) -> str:
    return state.get("next_agent") or "agent_main"


# ─── Specialist agent factory (mỗi agent bind tools riêng) ─────────────────────


def _make_specialist_node(agent_name: str, tools: list) -> Callable:
    bound_llm = llm.bind_tools(tools)
    sys_msg = _system_for(agent_name)

    async def node(state: AgentState) -> dict:
        messages: List[BaseMessage] = state.get("messages", [])
        input_messages = [sys_msg, *messages]
        response = await bound_llm.ainvoke(input_messages)
        return {"messages": [response]}

    node.__name__ = f"{agent_name}_node"
    return node


agent_expense_node = _make_specialist_node("agent_expense", EXPENSE_TOOLS)
agent_weather_node = _make_specialist_node("agent_weather", WEATHER_TOOLS)
agent_news_node = _make_specialist_node("agent_news", NEWS_TOOLS)


# ─── agent_main (không bind tools, chỉ tổng hợp) ───────────────────────────────


async def agent_main_node(state: AgentState) -> dict:
    messages: List[BaseMessage] = state.get("messages", [])
    input_messages = [_system_for("agent_main"), *messages]
    response = await llm.ainvoke(input_messages)
    return {"messages": [response]}


# ─── Tool node tuỳ biến: tự inject user_id từ state ────────────────────────────

def _make_tool_node(tools: list) -> Callable:
    tools_by_name = {t.name: t for t in tools}

    async def node(state: AgentState) -> dict:
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last_msg = messages[-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return {"messages": []}

        user_id = state.get("user_id", "")
        tool_messages: List[ToolMessage] = []

        for call in last_msg.tool_calls:
            name = call.get("name", "")
            args = dict(call.get("args") or {})
            tool_call_id = call.get("id", "")

            tool = tools_by_name.get(name)
            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"Tool '{name}' không khả dụng cho agent này.",
                        tool_call_id=tool_call_id,
                        name=name,
                    )
                )
                continue

            # Tự inject user_id (LLM không cần biết)
            if name in TOOLS_NEEDING_USER_ID:
                args["user_id"] = user_id

            try:
                result = await tool.ainvoke(args)
            except Exception as exc:  # noqa: BLE001 - tool errors phải được surface
                result = f"Lỗi khi gọi tool {name}: {exc}"

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=name,
                )
            )

        return {"messages": tool_messages}

    return node


tools_expense_node = _make_tool_node(EXPENSE_TOOLS)
tools_weather_node = _make_tool_node(WEATHER_TOOLS)
tools_news_node = _make_tool_node(NEWS_TOOLS)


# ─── Routing helpers ───────────────────────────────────────────────────────────


def _make_specialist_router(tools_node_name: str) -> Callable:
    """Sau khi specialist phản hồi:
    - Nếu AIMessage có `tool_calls` -> nhảy sang tool node tương ứng.
    - Ngược lại -> END (AIMessage của specialist chính là câu trả lời cuối).
    """

    def route(state: AgentState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return END
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return tools_node_name
        return END

    return route


# ─── Graph wiring ──────────────────────────────────────────────────────────────

workflow = StateGraph(state_schema=AgentState)

workflow.add_node("agent_router", agent_router_node)
workflow.add_node("agent_expense", agent_expense_node)
workflow.add_node("agent_weather", agent_weather_node)
workflow.add_node("agent_news", agent_news_node)
workflow.add_node("agent_main", agent_main_node)

workflow.add_node("tools_expense", tools_expense_node)
workflow.add_node("tools_weather", tools_weather_node)
workflow.add_node("tools_news", tools_news_node)

workflow.set_entry_point("agent_router")

workflow.add_conditional_edges(
    "agent_router",
    route_after_router,
    {
        "agent_expense": "agent_expense",
        "agent_weather": "agent_weather",
        "agent_news": "agent_news",
        "agent_main": "agent_main",
    },
)

workflow.add_conditional_edges(
    "agent_expense",
    _make_specialist_router("tools_expense"),
    {"tools_expense": "tools_expense", END: END},
)
workflow.add_conditional_edges(
    "agent_weather",
    _make_specialist_router("tools_weather"),
    {"tools_weather": "tools_weather", END: END},
)
workflow.add_conditional_edges(
    "agent_news",
    _make_specialist_router("tools_news"),
    {"tools_news": "tools_news", END: END},
)

# Sau khi tool chạy xong, quay lại đúng specialist để xử lý kết quả
workflow.add_edge("tools_expense", "agent_expense")
workflow.add_edge("tools_weather", "agent_weather")
workflow.add_edge("tools_news", "agent_news")

workflow.add_edge("agent_main", END)


memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)


# try:
#     # In sơ đồ ASCII ra terminal
#     # print(agent.get_graph())
#     # Hoặc Mermaid (dán vào https://mermaid.live để xem đẹp hơn)
#     print(agent.get_graph().draw_mermaid())
# except Exception as e:
#     print(e)
