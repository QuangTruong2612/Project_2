from typing import Annotated, TypedDict, Optional, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """State của graph multi-agent.

    `messages` là source of truth duy nhất cho ngữ cảnh hội thoại
    và kết quả tool (qua ToolMessage). Không còn dùng các trường
    `last_agent_response` / `tool_observations` để tránh trộn dữ liệu cũ.
    """

    # Thông tin định danh user (tự động inject vào tool args)
    user_id: str

    # Quyết định của router: agent_expense | agent_news | agent_weather | agent_main
    next_agent: Optional[str]

    # Lịch sử hội thoại + tool messages (được LangGraph reduce qua add_messages)
    messages: Annotated[List[BaseMessage], add_messages]
