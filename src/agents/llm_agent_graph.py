from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq

from src.core import settings
from src.agents import AgentState

llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama3-70b-8192",
    temperature=0.1  
)

def call_model(state: AgentState):
    """
    Node xử lý chính: LLM sẽ đọc tin nhắn và quyết định:
    - Trả lời người dùng ngay.
    - Hoặc yêu cầu gọi một Tool.
    """
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)


workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent",
)

workflow.add_edge("tools", "agent")

memory = MemorySaver()

app_agent = workflow.compile(checkpointer=memory) 