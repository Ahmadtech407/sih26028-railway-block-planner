"""
AI Section Controller Assistant Routes.
"""

from fastapi import APIRouter
from backend.schemas.api_models import AIChatRequest, AIChatResponse
from backend.services.agent_service import process_ai_chat

router = APIRouter(prefix="/ai", tags=["AI Section Controller"])


@router.post("/chat", response_model=AIChatResponse, summary="Natural language AI Section Controller assistant")
async def chat_assistant(request: AIChatRequest):
    """
    Communicates with the Google Antigravity / Gemini-powered AI Section Controller.
    Supports queries about track status, scheduling trade-offs, and operational decisions.
    """
    return await process_ai_chat(request)
