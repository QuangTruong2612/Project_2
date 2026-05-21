from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.llm_agent_graph import agent

router = APIRouter(prefix="/chat", tags=["Chat"])

# =========== INPUT PARSING ====================
class ChatRequest(BaseModel):
    message: str = Field(..., description="Tin nhắn của người dùng")
    user_id: str = Field(..., description="ID người dùng")
    session_id: Optional[str] = Field(
        None,
        description="ID phiên hội thoại. Nếu không truyền, mỗi request là 1 cuộc trò chuyện mới."
    )

# =========== RESPONSE PARSING =================
class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str = "success"


# =========== ENDPOINT ==========================
@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Gửi tin nhắn tới AI agent và nhận phản hồi.

    - `session_id` giúp duy trì lịch sử hội thoại qua nhiều lượt.
      Nếu không truyền, mỗi request sẽ là 1 phiên độc lập.
    """
    # Dùng session_id làm thread_id để MemorySaver giữ context hội thoại
    thread_id = request.session_id or str(uuid.uuid4())

    initial_state = {
        "user_id": request.user_id,
        "messages": [HumanMessage(content=request.message)],
    }
    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = await agent.ainvoke(initial_state, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    messages = final_state.get("messages", [])

    last_human_idx = next(
        (i for i, m in reversed(list(enumerate(messages))) if isinstance(m, HumanMessage)),
        -1,
    )
    current_turn_msgs = messages[last_human_idx + 1:] if last_human_idx >= 0 else messages
    
    ai_reply = next(
        (m.content for m in reversed(current_turn_msgs) if isinstance(m, AIMessage) and m.content.strip()),
        "Xin lỗi, mình chưa có câu trả lời cho câu này.",
    )

    return ChatResponse(
        response=ai_reply,
        session_id=thread_id,
    )
