"""
Study session API routes
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.study_service import StudySessionService
from app.services.deck_service import DeckService
from app.auth.dependencies import get_current_active_user
from app.core.database import get_supabase_client
from app.schemas.schemas import (
    StudySessionCreate,
    StudySessionResponse,
    StudySessionUpdate,
    CardInteractionCreate,
    CardInteractionResponse,
    QuizQuestionResponse,
    QuizAnswerRequest,
    QuizAnswerResponse,
    CardWithProgress
)

router = APIRouter(prefix="/study", tags=["study"])


async def get_study_service() -> StudySessionService:
    """Dependency to get study service"""
    supabase_client = get_supabase_client()
    return StudySessionService(supabase_client)


async def get_deck_service() -> DeckService:
    """Dependency to get deck service"""
    supabase_client = get_supabase_client()
    return DeckService(supabase_client)


@router.post("/sessions", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def create_study_session(
    session_create: StudySessionCreate,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Create a new study session"""
    
    # Verify deck belongs to user
    deck = await deck_service.get_deck_by_id(
        session_create.deck_id, 
        uuid.UUID(current_user["id"])
    )
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    session = await study_service.create_study_session(
        user_id=uuid.UUID(current_user["id"]),
        session_create=session_create
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create study session"
        )
    
    return session


@router.get("/sessions/{session_id}", response_model=StudySessionResponse)
async def get_study_session(
    session_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Get study session details"""
    
    session = await study_service.get_study_session(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    return session


@router.put("/sessions/{session_id}", response_model=StudySessionResponse)
async def update_study_session(
    session_id: uuid.UUID,
    session_update: StudySessionUpdate,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Update study session progress"""
    
    session = await study_service.update_study_session(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"]),
        session_update=session_update
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    return session


@router.post("/sessions/{session_id}/end", response_model=StudySessionResponse)
async def end_study_session(
    session_id: uuid.UUID,
    duration_minutes: int,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """End a study session"""
    
    session = await study_service.end_study_session(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"]),
        final_duration_minutes=duration_minutes
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    return session


@router.get("/sessions/{session_id}/cards", response_model=List[CardWithProgress])
async def get_study_cards(
    session_id: uuid.UUID,
    count: int = 10,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Get cards for study session using adaptive algorithm"""
    
    cards = await study_service.get_study_cards(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"]),
        count=count
    )
    
    return cards


@router.post("/interactions", response_model=CardInteractionResponse, status_code=status.HTTP_201_CREATED)
async def record_card_interaction(
    interaction: CardInteractionCreate,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Record a card interaction during study"""
    
    result = await study_service.record_card_interaction(
        interaction=interaction,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not record interaction"
        )
    
    return result


@router.get("/sessions/{session_id}/quiz/{card_id}", response_model=QuizQuestionResponse)
async def get_quiz_question(
    session_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Generate a quiz question for a specific card"""
    
    # Get session to determine deck and direction
    session = await study_service.get_study_session(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    
    question = await study_service.generate_quiz_question(
        card_id=card_id,
        deck_id=session.deck_id,
        direction=session.direction,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not generate quiz question"
        )
    
    return question


@router.post("/sessions/{session_id}/quiz", response_model=QuizAnswerResponse)
async def submit_quiz_answer(
    session_id: uuid.UUID,
    answer: QuizAnswerRequest,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Submit and evaluate a quiz answer"""
    
    result = await study_service.submit_quiz_answer(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"]),
        answer=answer
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not evaluate answer"
        )
    
    return result


@router.get("/sessions", response_model=List[StudySessionResponse])
async def get_user_study_sessions(
    deck_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Get user's study sessions"""
    
    sessions = await study_service.get_user_study_sessions(
        user_id=uuid.UUID(current_user["id"]),
        deck_id=deck_id,
        limit=limit
    )
    
    return sessions


@router.get("/sessions/{session_id}/statistics")
async def get_session_statistics(
    session_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    study_service: StudySessionService = Depends(get_study_service)
):
    """Get detailed statistics for a study session"""
    
    stats = await study_service.get_session_statistics(
        session_id=session_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session statistics not found"
        )
    
    return stats