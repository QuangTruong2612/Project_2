from typing import Annotated, TypedDict, Optional, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """State của graph multi-agent.

    `messages` là source of truth duy nhất cho ngữ cảnh hội thoại
    và kết quả tool (qua ToolMessage). Không còn dùng các trường
    `last_agent_response` / `tool_observations` để tránh trộn dữ liệu cũ.
    """

    user_id: str
    next_agent: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]
    router_retries: int
