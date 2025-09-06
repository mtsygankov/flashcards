"""
Deck management API routes
"""
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.deck_service import DeckService
from app.auth.dependencies import get_current_active_user
from app.core.database import get_supabase_client
from app.schemas.schemas import (
    DeckCreate, 
    DeckUpdate, 
    DeckResponse,
    DeckWithProgress
)

router = APIRouter(prefix="/decks", tags=["decks"])


async def get_deck_service() -> DeckService:
    """Dependency to get deck service"""
    supabase_client = get_supabase_client()
    return DeckService(supabase_client)


@router.post("/", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
async def create_deck(
    deck_create: DeckCreate,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Create a new deck"""
    deck = await deck_service.create_deck(
        user_id=uuid.UUID(current_user["id"]),
        deck_create=deck_create
    )
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create deck"
        )
    
    return deck


@router.get("/", response_model=List[DeckResponse])
async def get_user_decks(
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Get all decks for the current user"""
    return await deck_service.get_user_decks(uuid.UUID(current_user["id"]))


@router.get("/{deck_id}", response_model=DeckResponse)
async def get_deck(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Get a specific deck"""
    deck = await deck_service.get_deck_by_id(
        deck_id=deck_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return deck


@router.get("/{deck_id}/progress", response_model=DeckWithProgress)
async def get_deck_with_progress(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Get a deck with user progress information"""
    deck = await deck_service.get_deck_with_progress(
        deck_id=deck_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return deck


@router.put("/{deck_id}", response_model=DeckResponse)
async def update_deck(
    deck_id: uuid.UUID,
    deck_update: DeckUpdate,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Update a deck"""
    deck = await deck_service.update_deck(
        deck_id=deck_id,
        user_id=uuid.UUID(current_user["id"]),
        deck_update=deck_update
    )
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return deck


@router.delete("/{deck_id}")
async def delete_deck(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Delete a deck"""
    success = await deck_service.delete_deck(
        deck_id=deck_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    return {"message": "Deck deleted successfully"}


@router.post("/{deck_id}/study-time")
async def update_deck_study_time(
    deck_id: uuid.UUID,
    additional_seconds: int,
    current_user: dict = Depends(get_current_active_user),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Update deck study time"""
    # Verify deck belongs to user first
    deck = await deck_service.get_deck_by_id(
        deck_id=deck_id,
        user_id=uuid.UUID(current_user["id"])
    )
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    success = await deck_service.update_deck_study_time(deck_id, additional_seconds)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update study time"
        )
    
    return {"message": "Study time updated successfully"}