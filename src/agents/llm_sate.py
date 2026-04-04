from typing import Annotated, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # Lưu thông tin người dùng để không phải fetch Supabase nhiều lần
    user_profile: Optional[dict] 
    # Lưu trạng thái ví tiền hiện tại để Agent biết số dư mà không cần hỏi Tool
    current_balance: float