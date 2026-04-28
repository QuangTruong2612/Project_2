from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
import json
import inspect

from src.core import settings
from src.agents.llm_state import AgentState
from src.tools import AGENT_TOOLS_LIST, TOOLS_MAPPING
from src.prompts.prompts import AGENT_PROFILE

# llm 
llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.1
)


# build tool list
def build_tools_list(agent_name: str) -> str :
    tools = AGENT_TOOLS_LIST.get(agent_name, [])
    tool_lines = ['###   DANH SÁCH CÔNG CỤ CÓ SẴN (AVAILABLE TOOLS):\n']
    for i, tool in enumerate(tools, start=1):
        tool_lines.append(
            f"""{i}. {tool['name']}
   - Mô tả: {tool['description']}
   - Tham số: {tool['args']}"""
        )
    return '\n'.join(tool_lines)

# add tools list in AGENT_PROFILE
for agent_name in AGENT_PROFILE.keys():
    tool_list_str = build_tools_list(agent_name)
    AGENT_PROFILE[agent_name]["tools_list"] = tool_list_str

# Prompt template chung cho sub-agents (router/expense/news/weather)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "Bạn là {role}"),
    ("system", "Hệ thống hỗ trợ các công cụ sau: \n{tools_list}"),
    ("system", "{system_instruction}"),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{query}"),
    ("system", "Response của agent trước đó (nếu có): \n{last_agent_response}"),
    ("system", "Quan sát công cụ trong quá khứ: \n{tool_observations}"),
])

# Prompt template riêng cho agent_main:
# Đưa tool_observations lên trước, không có last_agent_response để tránh LLM anchor vào nội dung nhiễu
prompt_template_main = ChatPromptTemplate.from_messages([
    ("system", "Bạn là {role}"),
    ("system", "{system_instruction}"),
    ("system",
     "DƯỚI ĐÂY LÀ DỮ LIỆU THỰC TẾT DO HỆ THỐNG TRẢ VỀ — hãy đọc kỹ và chỉ dựa vào đây:\n"
     "-----\n{tool_observations}\n-----"),
    MessagesPlaceholder(variable_name="messages"),
    ("human", "{query}"),
])

# call agent (sub-agents)
async def call_agent(state: dict, agent_name: str) -> dict:
    profile = AGENT_PROFILE[agent_name]
    chain = prompt_template | llm

    messages = state.get("messages", [])

    # Format tool_observations từ list thành string có cấu trúc để LLM đọc dễ hơn
    raw_obs = state.get("tool_observations", [])
    tool_observations_str = "\n".join(raw_obs) if raw_obs else "(chưa có kết quả tool nào)"

    response = await chain.ainvoke({
        "role": profile['role'],
        "system_instruction": profile['system_instruction'],
        "query": state.get("query", ""),
        "messages": messages,
        "last_agent_response": state.get("last_agent_response", ""),
        "tool_observations": tool_observations_str,
        "tools_list": profile["tools_list"]
    })

    # Chỉ return các keys được update (không return full state)
    # Vì tool_observations dùng operator.add reducer, nếu return full state sẽ bị append 2 lần
    return {
        "last_agent_response": response.content,
        "last_agent": agent_name,
        "num_steps": state.get("num_steps", 0) + 1,
    }


# call agent_main với prompt template riêng, chỉ dựa vào tool_observations
async def call_agent_main_llm(state: dict) -> dict:
    profile = AGENT_PROFILE["agent_main"]
    chain = prompt_template_main | llm

    messages = state.get("messages", [])

    raw_obs = state.get("tool_observations", [])
    tool_observations_str = "\n".join(raw_obs) if raw_obs else "(chưa có dữ liệu nào được trả về)"

    print(f"[agent_main] tool_observations ({len(raw_obs)} entries):\n{tool_observations_str[:300]}")

    response = await chain.ainvoke({
        "role": profile['role'],
        "system_instruction": profile['system_instruction'],
        "query": state.get("query", ""),
        "messages": messages,
        "tool_observations": tool_observations_str,
    })

    return {
        "last_agent_response": response.content,
        "last_agent": "agent_main",
        "num_steps": state.get("num_steps", 0) + 1,
    }

def _format_tool_result(tool_name: str, results) -> str:
    """
    Chuyển kết quả tool thành văn bản có cấu trúc rõ ràng để LLM dễ đọc.
    Tránh để LLM tự parse raw Python dict → giảm hallucination.
    """
    # Chuỗi lỗi hoặc thông báo đơn giản
    if isinstance(results, str):
        return f"[{tool_name}]: {results}"

    # Danh sách dict (vd: kết quả get_expense_tool)
    if isinstance(results, list):
        if not results:
            return f"[{tool_name}]: Không có dữ liệu."

        SKIP_FIELDS = {'user_id', 'created_at'}
        TECHNICAL_FIELDS = {'id'}

        lines = [f"[{tool_name} — {len(results)} kết quả]"]
        for i, item in enumerate(results, 1):
            if not isinstance(item, dict):
                lines.append(f"  [{i}] {item}")
                continue

            # Các trường hiển thị chính (bỏ user_id, created_at)
            main_parts = []
            tech_parts = []
            for k, v in item.items():
                if k in SKIP_FIELDS:
                    continue
                if k in TECHNICAL_FIELDS:
                    tech_parts.append(f"{k}={v}")
                else:
                    main_parts.append(f"{k}: {v}")

            line = f"  [{i}] " + " | ".join(main_parts)
            if tech_parts:
                line += f"  ({', '.join(tech_parts)})"
            lines.append(line)
        return "\n".join(lines)

    # Dict đơn (vd: kết quả get_news_url)
    if isinstance(results, dict):
        SKIP_FIELDS = {'user_id', 'created_at'}
        parts = [f"{k}: {v}" for k, v in results.items() if k not in SKIP_FIELDS]
        return f"[{tool_name}]\n" + "\n".join(parts)

    return f"[{tool_name}]: {str(results)}"


# call tool
async def call_tool(state: dict) -> dict:
    action_text = state.get("last_agent_response", "")
    agent_name = state.get("last_agent")

    if "ACTION:" not in action_text:
        return {"tool_observations": [f"[No action found by {agent_name}]"]}

    print(f"--- ⚙️ CALLING TOOL FROM ({agent_name}) ---")

    # Extract tool name
    try:
        tool_name = action_text.split("ACTION:")[1].split("\n")[0].strip()
    except Exception:
        return {"tool_observations": ["[Error parsing ACTION name]"]}

    print(f"Tool requested: {tool_name}")

    # Check permission
    allowed_tools = AGENT_TOOLS_LIST.get(agent_name, [])
    allowed_names = [tool["name"] for tool in allowed_tools]

    if tool_name not in allowed_names:
        msg = f"[Tool '{tool_name}' NOT allowed for {agent_name}]"
        print(msg)
        return {"tool_observations": [msg]}

    # Parse arguments
    args = {}
    if "ARGUMENTS:" in action_text:
        args_text = action_text.split("ARGUMENTS:")[1].strip()

        # Simple extraction of JSON block
        if "{" in args_text:
            start = args_text.find("{")
            brace_count = 0
            for i in range(start, len(args_text)):
                if args_text[i] == "{": brace_count += 1
                elif args_text[i] == "}": brace_count -= 1
                if brace_count == 0:
                    args_text = args_text[start:i+1]
                    break
        try:
            args = json.loads(args_text)
        except json.JSONDecodeError:
            msg = f"[Failed to parse arguments: {args_text}]"
            print(msg)
            return {"tool_observations": [msg]}

    # Execute tool
    tool_func = TOOLS_MAPPING.get(tool_name)
    if not tool_func:
        msg = f"[Unknown tool: {tool_name}]"
        print(msg)
        return {"tool_observations": [msg]}

    try:
        if inspect.iscoroutinefunction(tool_func):
            results = await tool_func(**args)
        else:
            results = tool_func(**args)
    except Exception as e:
        results = f"Error executing tool: {str(e)}"

    # Format kết quả thành văn bản có cấu trúc (tránh LLM đọc raw dict)
    formatted = _format_tool_result(tool_name, results)
    print(f"Tool Result (formatted):\n{formatted}")

    # Chỉ return tool_observations mới + last_tool_results
    # operator.add reducer sẽ append formatted vào list hiện tại
    return {
        "tool_observations": [formatted],
        "last_tool_results": results,
    }


def route_from_router(state: dict) -> str:
    """
    Điều hướng từ agent_router:
    - Nếu ACTION chứa tên sub-agent -> đến sub-agent đó
    - Mọi trường hợp còn lại (chào hỏi, câu hỏi chung) -> agent_main
    """
    response = state.get("last_agent_response", "")
    sub_agents = ["agent_expense", "agent_news", "agent_weather"]

    if "ACTION:" in response:
        action_line = response.split("ACTION:")[1].split("\n")[0].strip()
        for agent_name in sub_agents:
            if agent_name in action_line:
                return agent_name

    return "agent_main"


def route_from_sub_agent(state: dict) -> str:
    """
    Điều hướng từ các sub-agent (expense/news/weather):
    - Nếu ACTION chứa tên tool -> đến tools
    - Nếu ACTION chứa agent_main hoặc không có ACTION -> agent_main
    """
    response = state.get("last_agent_response", "")

    if "ACTION:" in response:
        action_line = response.split("ACTION:")[1].split("\n")[0].strip()
        if "agent_main" in action_line:
            return "agent_main"
        return "tools"

    return "agent_main"


def route_after_tools(state: dict) -> str:
    """Sau khi tool chạy xong, quay lại đúng sub-agent đã gọi tool."""
    return state.get("last_agent", "agent_main")

# ─── Node definitions ──────────────────────────────────────────────────────────

async def call_agent_router(state: AgentState):
    print("--- 🧭 AGENT ROUTER ---")
    return await call_agent(state, agent_name="agent_router")

async def call_agent_main(state: AgentState):
    print("--- 🗣️ AGENT MAIN (final response) ---")
    return await call_agent_main_llm(state)

async def call_agent_expense(state: AgentState):
    print("--- 💰 AGENT EXPENSE ---")
    return await call_agent(state, agent_name="agent_expense")

async def call_agent_news(state: AgentState):
    print("--- 📰 AGENT NEWS ---")
    return await call_agent(state, agent_name="agent_news")

async def call_agent_weather(state: AgentState):
    print("--- 🌤️ AGENT WEATHER ---")
    return await call_agent(state, agent_name="agent_weather")

async def call_tools(state: AgentState):
    return await call_tool(state)


# ─── Graph construction ─────────────────────────────────────────────────────────

workflow = StateGraph(state_schema=AgentState)

# Add nodes
workflow.add_node("agent_router", call_agent_router)
workflow.add_node("agent_main", call_agent_main)
workflow.add_node("agent_expense", call_agent_expense)
workflow.add_node("agent_news", call_agent_news)
workflow.add_node("agent_weather", call_agent_weather)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent_router")

workflow.add_conditional_edges(
    "agent_router",
    route_from_router,
    {
        "agent_expense": "agent_expense",
        "agent_news": "agent_news",
        "agent_weather": "agent_weather",
        "agent_main": "agent_main",
    }
)

for node in ["agent_expense", "agent_news", "agent_weather"]:
    workflow.add_conditional_edges(
        node,
        route_from_sub_agent,
        {
            "tools": "tools",
            "agent_main": "agent_main",
        }
    )

routing_config = {
    "agent_expense": "agent_expense",
    "agent_news": "agent_news",
    "agent_weather": "agent_weather",
    "agent_main": "agent_main",
}
workflow.add_conditional_edges("tools", route_after_tools, routing_config)

workflow.add_edge("agent_main", END)


memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)
