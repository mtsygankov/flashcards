"""
Card service for CRUD operations and card management
"""
from typing import List, Optional
import uuid
from datetime import datetime
from supabase import Client

from app.schemas.schemas import (
    CardCreate, 
    CardUpdate, 
    CardResponse,
    CardWithProgress,
    UserCardProgressResponse,
    PaginationParams,
    SearchParams,
    PaginatedResponse
)


class CardService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def create_card(self, deck_id: uuid.UUID, card_create: CardCreate) -> Optional[CardResponse]:
        """Create a new card in a deck"""
        try:
            card_data = {
                "deck_id": str(deck_id),
                "hanzi": card_create.hanzi,
                "pinyin": card_create.pinyin,
                "english": card_create.english,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("cards").insert(card_data).execute()
            
            if response.data:
                return CardResponse(**response.data[0])
            
            return None
        except Exception as e:
            print(f"Error creating card: {e}")
            return None
    
    async def get_deck_cards(
        self, 
        deck_id: uuid.UUID, 
        pagination: Optional[PaginationParams] = None,
        search: Optional[SearchParams] = None
    ) -> List[CardResponse]:
        """Get all cards in a deck with optional pagination and search"""
        try:
            query = self.supabase.table("cards").select("*").eq("deck_id", str(deck_id))
            
            # Apply search filter
            if search and search.query:
                # Simple text search across all fields
                # In a more sophisticated implementation, you might use full-text search
                query = query.or_(
                    f"hanzi.ilike.%{search.query}%,"
                    f"pinyin.ilike.%{search.query}%,"
                    f"english.ilike.%{search.query}%"
                )
            
            # Apply sorting
            if search and search.sort_by:
                order_clause = f"{search.sort_by}.{search.sort_order}"
                query = query.order(order_clause)
            else:
                query = query.order("created_at.asc")
            
            # Apply pagination
            if pagination:
                query = query.range(pagination.offset, pagination.offset + pagination.size - 1)
            
            response = query.execute()
            
            return [CardResponse(**card) for card in response.data]
        except Exception as e:
            print(f"Error getting deck cards: {e}")
            return []
    
    async def get_card_by_id(self, card_id: uuid.UUID) -> Optional[CardResponse]:
        """Get card by ID"""
        try:
            response = self.supabase.table("cards").select("*").eq("id", str(card_id)).execute()
            
            if response.data:
                return CardResponse(**response.data[0])
            
            return None
        except Exception as e:
            print(f"Error getting card by ID: {e}")
            return None
    
    async def get_card_with_progress(self, card_id: uuid.UUID, user_id: uuid.UUID) -> Optional[CardWithProgress]:
        """Get card with user progress"""
        try:
            card = await self.get_card_by_id(card_id)
            if not card:
                return None
            
            # Get user progress for this card
            progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).eq("card_id", str(card_id)).execute()
            
            progress = None
            if progress_response.data:
                progress_data = progress_response.data[0]
                progress = UserCardProgressResponse(**progress_data)
            
            return CardWithProgress(**card.dict(), user_progress=progress)
            
        except Exception as e:
            print(f"Error getting card with progress: {e}")
            return None
    
    async def update_card(self, card_id: uuid.UUID, card_update: CardUpdate) -> Optional[CardResponse]:
        """Update a card"""
        try:
            update_data = card_update.dict(exclude_unset=True)
            
            if update_data:
                response = self.supabase.table("cards").update(update_data).eq("id", str(card_id)).execute()
                
                if response.data:
                    return CardResponse(**response.data[0])
            
            return await self.get_card_by_id(card_id)
        except Exception as e:
            print(f"Error updating card: {e}")
            return None
    
    async def delete_card(self, card_id: uuid.UUID) -> bool:
        """Delete a card"""
        try:
            response = self.supabase.table("cards").delete().eq("id", str(card_id)).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error deleting card: {e}")
            return False
    
    async def delete_cards_bulk(self, card_ids: List[uuid.UUID]) -> int:
        """Delete multiple cards"""
        try:
            deleted_count = 0
            for card_id in card_ids:
                if await self.delete_card(card_id):
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            print(f"Error bulk deleting cards: {e}")
            return 0
    
    async def get_cards_count(self, deck_id: uuid.UUID, search: Optional[SearchParams] = None) -> int:
        """Get total count of cards in a deck with optional search"""
        try:
            query = self.supabase.table("cards").select("id", count="exact").eq("deck_id", str(deck_id))
            
            # Apply search filter
            if search and search.query:
                query = query.or_(
                    f"hanzi.ilike.%{search.query}%,"
                    f"pinyin.ilike.%{search.query}%,"
                    f"english.ilike.%{search.query}%"
                )
            
            response = query.execute()
            return response.count or 0
        except Exception as e:
            print(f"Error getting cards count: {e}")
            return 0
    
    async def get_paginated_cards(
        self, 
        deck_id: uuid.UUID,
        pagination: PaginationParams,
        search: Optional[SearchParams] = None
    ) -> PaginatedResponse:
        """Get paginated cards with search"""
        try:
            # Get total count
            total = await self.get_cards_count(deck_id, search)
            
            # Get cards for current page
            cards = await self.get_deck_cards(deck_id, pagination, search)
            
            return PaginatedResponse(
                items=cards,
                total=total,
                page=pagination.page,
                size=pagination.size,
                pages=(total + pagination.size - 1) // pagination.size if total > 0 else 0
            )
        except Exception as e:
            print(f"Error getting paginated cards: {e}")
            return PaginatedResponse(
                items=[],
                total=0,
                page=pagination.page,
                size=pagination.size,
                pages=0
            )
    
    async def verify_card_belongs_to_user(self, card_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Verify that a card belongs to a user's deck"""
        try:
            # Get the card's deck
            card_response = self.supabase.table("cards").select("deck_id").eq("id", str(card_id)).execute()
            
            if not card_response.data:
                return False
            
            deck_id = card_response.data[0]["deck_id"]
            
            # Check if the deck belongs to the user
            deck_response = self.supabase.table("decks").select("id").eq("id", deck_id).eq("user_id", str(user_id)).execute()
            
            return len(deck_response.data) > 0
        except Exception as e:
            print(f"Error verifying card ownership: {e}")
            return False
    
    async def get_random_cards_for_study(
        self, 
        deck_id: uuid.UUID, 
        user_id: uuid.UUID, 
        limit: int = 10
    ) -> List[CardWithProgress]:
        """Get random cards from a deck for study session"""
        try:
            # Get all cards in the deck
            cards = await self.get_deck_cards(deck_id)
            
            # For each card, get user progress
            cards_with_progress = []
            for card in cards:
                card_with_progress = await self.get_card_with_progress(card.id, user_id)
                if card_with_progress:
                    cards_with_progress.append(card_with_progress)
            
            # For now, return first N cards (in a real implementation, 
            # this would use the adaptive learning algorithm)
            return cards_with_progress[:limit]
            
        except Exception as e:
            print(f"Error getting random cards for study: {e}")
            return []