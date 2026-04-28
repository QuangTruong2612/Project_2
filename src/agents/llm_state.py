from typing import Annotated, TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator

class AgentState(TypedDict):
    query: str
    user_id: str
    last_agent_response: str
    last_agent: str
    tool_observations: Annotated[List[str], operator.add]
    num_steps: int
    messages: Annotated[List[BaseMessage], add_messages]