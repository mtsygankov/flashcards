"""
Deck service for CRUD operations and deck management
"""
from typing import List, Optional
import uuid
from datetime import datetime
from supabase import Client

from app.schemas.schemas import (
    DeckCreate, 
    DeckUpdate, 
    DeckResponse,
    UserDeckProgress,
    DeckWithProgress
)


class DeckService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def create_deck(self, user_id: uuid.UUID, deck_create: DeckCreate) -> Optional[DeckResponse]:
        """Create a new deck for a user"""
        try:
            deck_data = {
                "user_id": str(user_id),
                "name": deck_create.name,
                "description": deck_create.description,
                "created_at": datetime.utcnow().isoformat(),
                "total_study_time": 0
            }
            
            response = self.supabase.table("decks").insert(deck_data).execute()
            
            if response.data:
                deck_data = response.data[0]
                deck_data["card_count"] = 0  # New deck has no cards
                return DeckResponse(**deck_data)
            
            return None
        except Exception as e:
            print(f"Error creating deck: {e}")
            return None
    
    async def get_user_decks(self, user_id: uuid.UUID) -> List[DeckResponse]:
        """Get all decks for a user"""
        try:
            response = self.supabase.table("decks").select("*").eq("user_id", str(user_id)).execute()
            
            decks = []
            for deck_data in response.data:
                # Get card count for each deck
                cards_response = self.supabase.table("cards").select("id", count="exact").eq("deck_id", deck_data["id"]).execute()
                deck_data["card_count"] = cards_response.count or 0
                
                decks.append(DeckResponse(**deck_data))
            
            return decks
        except Exception as e:
            print(f"Error getting user decks: {e}")
            return []
    
    async def get_deck_by_id(self, deck_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Optional[DeckResponse]:
        """Get deck by ID, optionally filter by user"""
        try:
            query = self.supabase.table("decks").select("*").eq("id", str(deck_id))
            
            if user_id:
                query = query.eq("user_id", str(user_id))
            
            response = query.execute()
            
            if response.data:
                deck_data = response.data[0]
                # Get card count
                cards_response = self.supabase.table("cards").select("id", count="exact").eq("deck_id", deck_data["id"]).execute()
                deck_data["card_count"] = cards_response.count or 0
                
                return DeckResponse(**deck_data)
            
            return None
        except Exception as e:
            print(f"Error getting deck by ID: {e}")
            return None
    
    async def update_deck(self, deck_id: uuid.UUID, user_id: uuid.UUID, deck_update: DeckUpdate) -> Optional[DeckResponse]:
        """Update a deck"""
        try:
            update_data = deck_update.dict(exclude_unset=True)
            
            if update_data:
                response = self.supabase.table("decks").update(update_data).eq("id", str(deck_id)).eq("user_id", str(user_id)).execute()
                
                if response.data:
                    return await self.get_deck_by_id(deck_id, user_id)
            
            return await self.get_deck_by_id(deck_id, user_id)
        except Exception as e:
            print(f"Error updating deck: {e}")
            return None
    
    async def delete_deck(self, deck_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a deck and all its cards"""
        try:
            response = self.supabase.table("decks").delete().eq("id", str(deck_id)).eq("user_id", str(user_id)).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error deleting deck: {e}")
            return False
    
    async def get_deck_with_progress(self, deck_id: uuid.UUID, user_id: uuid.UUID) -> Optional[DeckWithProgress]:
        """Get deck with user progress information"""
        try:
            deck = await self.get_deck_by_id(deck_id, user_id)
            if not deck:
                return None
            
            # Get all cards in the deck
            cards_response = self.supabase.table("cards").select("id").eq("deck_id", str(deck_id)).execute()
            
            if not cards_response.data:
                # Empty deck
                progress = UserDeckProgress(
                    cards_new=0,
                    cards_learning=0,
                    cards_review=0,
                    cards_mastered=0,
                    average_accuracy=0.0
                )
                return DeckWithProgress(**deck.dict(), user_progress=progress)
            
            card_ids = [card["id"] for card in cards_response.data]
            
            # Get user progress for all cards in the deck
            progress_counts = {
                "cards_new": 0,
                "cards_learning": 0,
                "cards_review": 0,
                "cards_mastered": 0
            }
            
            total_accuracy = 0.0
            cards_with_attempts = 0
            
            for card_id in card_ids:
                progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).eq("card_id", card_id).execute()
                
                if progress_response.data:
                    progress_data = progress_response.data[0]
                    mastery_level = progress_data.get("mastery_level", 0)
                    
                    if mastery_level == 0:
                        progress_counts["cards_new"] += 1
                    elif mastery_level == 1:
                        progress_counts["cards_learning"] += 1
                    elif mastery_level == 2:
                        progress_counts["cards_review"] += 1
                    elif mastery_level == 3:
                        progress_counts["cards_mastered"] += 1
                    
                    # Calculate accuracy for this card
                    quiz_attempts = progress_data.get("quiz_attempts", 0)
                    if quiz_attempts > 0:
                        quiz_correct = progress_data.get("quiz_correct", 0)
                        accuracy = quiz_correct / quiz_attempts
                        total_accuracy += accuracy
                        cards_with_attempts += 1
                else:
                    # No progress data means new card
                    progress_counts["cards_new"] += 1
            
            # Calculate average accuracy
            average_accuracy = total_accuracy / cards_with_attempts if cards_with_attempts > 0 else 0.0
            
            progress = UserDeckProgress(
                **progress_counts,
                average_accuracy=average_accuracy
            )
            
            return DeckWithProgress(**deck.dict(), user_progress=progress)
            
        except Exception as e:
            print(f"Error getting deck with progress: {e}")
            return None
    
    async def update_deck_study_time(self, deck_id: uuid.UUID, additional_seconds: int) -> bool:
        """Add study time to a deck"""
        try:
            # Get current study time
            deck = await self.get_deck_by_id(deck_id)
            if not deck:
                return False
            
            new_total = deck.total_study_time + additional_seconds
            
            response = self.supabase.table("decks").update({
                "total_study_time": new_total,
                "last_studied_at": datetime.utcnow().isoformat()
            }).eq("id", str(deck_id)).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating deck study time: {e}")
            return False