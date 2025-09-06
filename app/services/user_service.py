"""
User service for CRUD operations
"""
from typing import List, Optional
import uuid
from datetime import datetime
from supabase import Client

from app.schemas.schemas import (
    UserCreate, 
    UserUpdate, 
    UserResponse, 
    UserStatisticsResponse
)


class UserService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_all_users(self) -> List[UserResponse]:
        """Get all users with basic information"""
        try:
            response = self.supabase.table("users").select("*").execute()
            
            return [UserResponse(**user) for user in response.data]
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[UserResponse]:
        """Get user by ID"""
        try:
            response = self.supabase.table("users").select("*").eq("id", str(user_id)).execute()
            
            if response.data:
                return UserResponse(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username"""
        try:
            response = self.supabase.table("users").select("*").eq("username", username).execute()
            
            if response.data:
                return UserResponse(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
    
    async def update_user(self, user_id: uuid.UUID, user_update: UserUpdate) -> Optional[UserResponse]:
        """Update user information"""
        try:
            update_data = user_update.dict(exclude_unset=True)
            
            if update_data:
                response = self.supabase.table("users").update(update_data).eq("id", str(user_id)).execute()
                
                if response.data:
                    return UserResponse(**response.data[0])
            
            return await self.get_user_by_id(user_id)
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete user and all related data"""
        try:
            # Delete user (cascading deletes will handle related data)
            response = self.supabase.table("users").delete().eq("id", str(user_id)).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    async def get_user_statistics(self, user_id: uuid.UUID) -> Optional[UserStatisticsResponse]:
        """Get user statistics"""
        try:
            response = self.supabase.table("user_statistics").select("*").eq("user_id", str(user_id)).execute()
            
            if response.data:
                return UserStatisticsResponse(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user statistics: {e}")
            return None
    
    async def update_last_active(self, user_id: uuid.UUID) -> bool:
        """Update user's last active timestamp"""
        try:
            update_data = {"last_active_at": datetime.utcnow().isoformat()}
            response = self.supabase.table("users").update(update_data).eq("id", str(user_id)).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating last active: {e}")
            return False
    
    async def get_user_deck_count(self, user_id: uuid.UUID) -> int:
        """Get count of decks for a user"""
        try:
            response = self.supabase.table("decks").select("id", count="exact").eq("user_id", str(user_id)).execute()
            
            return response.count or 0
        except Exception as e:
            print(f"Error getting deck count: {e}")
            return 0
    
    async def get_user_total_cards(self, user_id: uuid.UUID) -> int:
        """Get total number of cards across all user's decks"""
        try:
            # Get all decks for the user
            decks_response = self.supabase.table("decks").select("id").eq("user_id", str(user_id)).execute()
            
            if not decks_response.data:
                return 0
            
            deck_ids = [deck["id"] for deck in decks_response.data]
            
            # Count cards in all user's decks
            total_cards = 0
            for deck_id in deck_ids:
                cards_response = self.supabase.table("cards").select("id", count="exact").eq("deck_id", deck_id).execute()
                total_cards += cards_response.count or 0
            
            return total_cards
        except Exception as e:
            print(f"Error getting total cards: {e}")
            return 0
    
    async def get_users_with_stats(self) -> List[dict]:
        """Get all users with their basic statistics"""
        try:
            users = await self.get_all_users()
            users_with_stats = []
            
            for user in users:
                stats = await self.get_user_statistics(user.id)
                deck_count = await self.get_user_deck_count(user.id)
                total_cards = await self.get_user_total_cards(user.id)
                
                user_data = {
                    "user": user,
                    "statistics": stats,
                    "deck_count": deck_count,
                    "total_cards": total_cards
                }
                users_with_stats.append(user_data)
            
            return users_with_stats
        except Exception as e:
            print(f"Error getting users with stats: {e}")
            return []