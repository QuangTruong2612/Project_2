from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

from langchain_core.messages import HumanMessage, AIMessage

# =========== INPUT PARSING ====================
class ChatRequest(BaseModel):
    message: str = Field()
    user_id: str = Field()
    session_id: Optional[str] = "default_session"

# =========== RESPONSE PARSING =================
class ChatResponse(BaseModel):
    response: str
    status: str = "success"
