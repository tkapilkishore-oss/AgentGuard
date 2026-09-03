"""FastAPI Route endpoints for AgentGuard Conversational Brain."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.schemas import ApiResponse
from backend.app.conversational.models import AssistantResponse, ConversationSession
from backend.app.conversational.orchestrator import get_conversational_brain
from backend.app.db.session import get_db

router = APIRouter(prefix="/conversational", tags=["Conversational Brain"])


class ConversationalQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User conversational query or instruction")
    session_id: str | None = Field(default=None, description="Optional conversation session ID")
    user_id: str = Field(default="user-001", description="User ID associated with the session")


@router.post("/query", response_model=ApiResponse[AssistantResponse])
def conversational_query(
    payload: ConversationalQueryRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[AssistantResponse]:
    """Processes a user conversational query with multi-turn session tracking,

    retrieval/live routing, and evidence-grounded response generation.
    """
    brain = get_conversational_brain()
    response = brain.process_query(
        query=payload.query,
        session_id=payload.session_id,
        user_id=payload.user_id,
        db=db,
    )
    return ApiResponse.ok(response)


@router.get("/session/{session_id}", response_model=ApiResponse[ConversationSession])
def get_session(session_id: str) -> ApiResponse[ConversationSession]:
    """Inspects active dialogue state and turn history for a session."""
    brain = get_conversational_brain()
    session = brain.dialogue_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    return ApiResponse.ok(session)


@router.delete("/session/{session_id}", response_model=ApiResponse[dict[str, Any]])
def reset_session(session_id: str) -> ApiResponse[dict[str, Any]]:
    """Resets an active conversation session."""
    brain = get_conversational_brain()
    success = brain.dialogue_manager.reset_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    session = brain.dialogue_manager.get_session(session_id)
    return ApiResponse.ok({
        "session_id": session_id,
        "status": "reset",
        "turn_count": session.turn_count if session else 0,
        "turns": session.turns if session else [],
    })
