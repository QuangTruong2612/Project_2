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

# Specialist dùng model đủ mạnh để tool-calling ổn định.
# llama-3.1-8b-instant quá nhỏ: hay bỏ qua tool_calls, tự sinh text thay vì
# gọi tool → agent_answer hallucinate xác nhận giả.
llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.1,
)
    
# agent_answer cần tổng hợp và format output — dùng cùng model mạnh.
llm_answer = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.2,    
)

# Router quyết định luồng — nếu sai sẽ cascade sang sai tool, nên dùng model
# mạnh hơn để giảm xác suất misroute. Chỉ chạy 1 lần / turn nên cost không
# tăng đáng kể. 
router_base_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
)


# ─── Tool buckets cho từng specialist ──────────────────────────────────────────

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
        "agent_expense", "agent_weather", "agent_news", "agent_answer"
    ] = Field(
        description=(
            "Tên agent sẽ xử lý yêu cầu mới nhất của người dùng. "
            "Chọn 1 trong 4: agent_expense | agent_weather | agent_news | agent_answer."
        )
    )


router_llm = router_base_llm.with_structured_output(RouteDecision)


def _system_for(agent_name: str) -> SystemMessage:
    profile = AGENT_PROFILE[agent_name]
    return SystemMessage(content=f"{profile['role']}\n{profile['system_instruction']}")


async def agent_router_node(state: AgentState) -> dict:
    """Phân loại intent của user và chọn agent kế tiếp."""
    messages: List[BaseMessage] = state.get("messages", [])
    routing_input: List[BaseMessage] = [_system_for("agent_router"), *messages]
    decision: RouteDecision = await router_llm.ainvoke(routing_input)
    # Reset retry khi router chạy lại (dù lần đầu hay retry)
    return {"next_agent": decision.next_agent, "router_retries": state.get("router_retries", 0)}


def route_after_router(state: AgentState) -> str:
    return state.get("next_agent") or "agent_answer"


# ─── Specialist agent factory ────────────────────────────────────────────────
# Specialist dùng tool_choice="auto": model tự quyết định có gọi tool hay không.
# Nếu không gọi tool (thiếu info, misroute...), specialist router sẽ đưa
# trở về agent_router để tìm agent đúng (tối đa _MAX_RETRIES lần).
_MAX_RETRIES = 2


def _make_specialist_node(agent_name: str, tools: list) -> Callable:
    bound_llm = llm.bind_tools(tools) 
    sys_msg = _system_for(agent_name)

    async def node(state: AgentState) -> dict:
        messages: List[BaseMessage] = state.get("messages", [])
        input_messages = [sys_msg, *messages]
        response = await bound_llm.ainvoke(input_messages)
        # Debug: log xem có tool_calls không
        has_calls = bool(getattr(response, "tool_calls", None))
        print(f"[{agent_name}] tool_calls={has_calls} | content={str(response.content)[:80]}")
        return {"messages": [response]}

    node.__name__ = f"{agent_name}_node"
    return node


agent_expense_node = _make_specialist_node("agent_expense", EXPENSE_TOOLS)
agent_weather_node = _make_specialist_node("agent_weather", WEATHER_TOOLS)
agent_news_node = _make_specialist_node("agent_news", NEWS_TOOLS)


# ─── agent_answer (không bind tool, chốt câu trả lời cuối) ─────────────────────


async def agent_answer_node(state: AgentState) -> dict:
    """Node trả lời DUY NHẤT cho mọi flow.

    Đọc toàn bộ `messages` (bao gồm các `ToolMessage` nếu có) và sinh câu
    trả lời tự nhiên, đúng định dạng, gửi thẳng tới user. KHÔNG bind tool
    nào — không thể trigger tool call mới, triệt tiêu nguy cơ lặp tool.
    """
    messages: List[BaseMessage] = state.get("messages", [])
    input_messages = [_system_for("agent_answer"), *messages]
    response = await llm_answer.ainvoke(input_messages)
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
    - Có tool_calls → chạy tool rồi đi agent_answer.
    - Không có tool_calls (misroute / thiếu info):
      • Còn retry → retry_gate (tăng counter rồi quay agent_router).
      • Hết retry → agent_answer (fallback cuối).
    """

    def route(state: AgentState) -> str:
        messages = state.get("messages", [])
        if not messages:
            return "retry_gate"
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return tools_node_name
        retries = state.get("router_retries", 0)
        if retries < _MAX_RETRIES:
            print(f"[specialist_router] no tool_calls, retry {retries+1}/{_MAX_RETRIES}")
            return "retry_gate"
        print("[specialist_router] max retries, fallback agent_answer")
        return "agent_answer"

    return route


async def retry_gate_node(state: AgentState) -> dict:
    """Tăng router_retries và thêm SystemMessage để phá loop, hướng dẫn router chuyển hướng."""
    warning = SystemMessage(content="SYSTEM WARNING: Agent trước đó không thể gọi tool. BẮT BUỘC chọn một agent KHÁC, hoặc chọn 'agent_answer' để trả lời user.")
    return {
        "router_retries": state.get("router_retries", 0) + 1,
        "messages": [warning]
    }


# ─── Graph wiring ──────────────────────────────────────────────────────────────

workflow = StateGraph(state_schema=AgentState)

workflow.add_node("agent_router", agent_router_node)
workflow.add_node("agent_expense", agent_expense_node)
workflow.add_node("agent_weather", agent_weather_node)
workflow.add_node("agent_news", agent_news_node)
workflow.add_node("agent_answer", agent_answer_node)
workflow.add_node("retry_gate", retry_gate_node)  # tăng counter → quay router

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
        "agent_answer": "agent_answer",
    },
)

_SPECIALIST_DESTS = {
    "tools_expense": "tools_expense",
    "tools_weather": "tools_weather",
    "tools_news": "tools_news",
    "retry_gate": "retry_gate",
    "agent_answer": "agent_answer",
}

workflow.add_conditional_edges(
    "agent_expense",
    _make_specialist_router("tools_expense"),
    {"tools_expense": "tools_expense", "retry_gate": "retry_gate", "agent_answer": "agent_answer"},
)
workflow.add_conditional_edges(
    "agent_weather",
    _make_specialist_router("tools_weather"),
    {"tools_weather": "tools_weather", "retry_gate": "retry_gate", "agent_answer": "agent_answer"},
)
workflow.add_conditional_edges(
    "agent_news",
    _make_specialist_router("tools_news"),
    {"tools_news": "tools_news", "retry_gate": "retry_gate", "agent_answer": "agent_answer"},
)

# retry_gate → agent_router (với counter đã tăng)
workflow.add_edge("retry_gate", "agent_router")

# Sau khi tool chạy xong → agent_answer (KHÔNG quay lại specialist)
workflow.add_edge("tools_expense", "agent_answer")
workflow.add_edge("tools_weather", "agent_answer")
workflow.add_edge("tools_news", "agent_answer")

workflow.add_edge("agent_answer", END)


memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)
