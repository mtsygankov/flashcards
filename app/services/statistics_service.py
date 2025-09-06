"""
Statistics service for tracking and analyzing user learning progress
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from supabase import Client


@dataclass
class LearningStats:
    """Container for learning statistics"""
    total_study_time_minutes: int
    total_cards_studied: int
    total_quiz_attempts: int
    total_correct_answers: int
    overall_accuracy: float
    study_streak_days: int
    cards_by_mastery: Dict[str, int]
    recent_sessions_count: int
    average_session_duration: float


@dataclass
class DeckStats:
    """Container for deck-specific statistics"""
    deck_id: str
    deck_name: str
    total_cards: int
    cards_studied: int
    study_progress_percentage: float
    mastery_distribution: Dict[str, int]
    average_accuracy: float
    total_study_time_minutes: int
    last_studied_at: Optional[datetime]


@dataclass
class CardStats:
    """Container for card-specific statistics"""
    card_id: str
    hanzi: str
    pinyin: str
    english: str
    mastery_level: int
    difficulty_score: float
    quiz_attempts: int
    quiz_correct: int
    accuracy_rate: float
    first_studied: Optional[datetime]
    last_studied: Optional[datetime]
    study_time_seconds: int


class StatisticsService:
    """Service for generating learning statistics and analytics"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def get_user_overview_stats(self, user_id: uuid.UUID) -> LearningStats:
        """Get overall learning statistics for a user"""
        
        try:
            # Get user statistics record
            user_stats_response = self.supabase.table("user_statistics").select("*").eq("user_id", str(user_id)).execute()
            
            # Get user card progress
            progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).execute()
            
            # Get recent study sessions (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            sessions_response = self.supabase.table("study_sessions").select("*").eq("user_id", str(user_id)).gte("created_at", thirty_days_ago.isoformat()).execute()
            
            # Calculate statistics
            if user_stats_response.data:
                user_stats = user_stats_response.data[0]
                total_study_time = user_stats.get("study_time_minutes", 0)
                total_quiz_attempts = user_stats.get("total_quiz_attempts", 0)
                total_correct = user_stats.get("total_correct_answers", 0)
            else:
                total_study_time = 0
                total_quiz_attempts = 0
                total_correct = 0
            
            # Calculate mastery distribution
            mastery_counts = {"new": 0, "learning": 0, "review": 0, "mastered": 0}
            total_cards_studied = len(progress_response.data)
            
            for progress in progress_response.data:
                mastery_level = progress.get("mastery_level", 0)
                if mastery_level == 0:
                    mastery_counts["new"] += 1
                elif mastery_level == 1:
                    mastery_counts["learning"] += 1
                elif mastery_level == 2:
                    mastery_counts["review"] += 1
                else:
                    mastery_counts["mastered"] += 1
            
            # Calculate overall accuracy
            overall_accuracy = total_correct / total_quiz_attempts if total_quiz_attempts > 0 else 0.0
            
            # Calculate recent sessions stats
            recent_sessions = sessions_response.data
            recent_sessions_count = len(recent_sessions)
            
            total_recent_duration = sum(session.get("session_duration", 0) for session in recent_sessions)
            average_session_duration = total_recent_duration / recent_sessions_count if recent_sessions_count > 0 else 0.0
            
            # Calculate study streak (simplified - consecutive days with sessions)
            study_streak = await self._calculate_study_streak(user_id)
            
            return LearningStats(
                total_study_time_minutes=total_study_time,
                total_cards_studied=total_cards_studied,
                total_quiz_attempts=total_quiz_attempts,
                total_correct_answers=total_correct,
                overall_accuracy=overall_accuracy,
                study_streak_days=study_streak,
                cards_by_mastery=mastery_counts,
                recent_sessions_count=recent_sessions_count,
                average_session_duration=average_session_duration
            )
            
        except Exception as e:
            print(f"Error getting user overview stats: {e}")
            return LearningStats(
                total_study_time_minutes=0,
                total_cards_studied=0,
                total_quiz_attempts=0,
                total_correct_answers=0,
                overall_accuracy=0.0,
                study_streak_days=0,
                cards_by_mastery={"new": 0, "learning": 0, "review": 0, "mastered": 0},
                recent_sessions_count=0,
                average_session_duration=0.0
            )
    
    async def get_deck_statistics(self, user_id: uuid.UUID, deck_id: uuid.UUID) -> Optional[DeckStats]:
        """Get statistics for a specific deck"""
        
        try:
            # Get deck information
            deck_response = self.supabase.table("decks").select("*").eq("id", str(deck_id)).eq("user_id", str(user_id)).execute()
            
            if not deck_response.data:
                return None
            
            deck_data = deck_response.data[0]
            
            # Get all cards in the deck
            cards_response = self.supabase.table("cards").select("id").eq("deck_id", str(deck_id)).execute()
            
            total_cards = len(cards_response.data)
            card_ids = [card["id"] for card in cards_response.data]
            
            if not card_ids:
                return DeckStats(
                    deck_id=str(deck_id),
                    deck_name=deck_data["name"],
                    total_cards=0,
                    cards_studied=0,
                    study_progress_percentage=0.0,
                    mastery_distribution={"new": 0, "learning": 0, "review": 0, "mastered": 0},
                    average_accuracy=0.0,
                    total_study_time_minutes=0,
                    last_studied_at=None
                )
            
            # Get user progress for all cards in the deck
            progress_data = []
            for card_id in card_ids:
                progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).eq("card_id", card_id).execute()
                
                if progress_response.data:
                    progress_data.append(progress_response.data[0])
            
            # Calculate statistics
            cards_studied = len(progress_data)
            study_progress_percentage = (cards_studied / total_cards) * 100 if total_cards > 0 else 0.0
            
            # Mastery distribution
            mastery_counts = {"new": 0, "learning": 0, "review": 0, "mastered": 0}
            total_attempts = 0
            total_correct = 0
            
            for progress in progress_data:
                mastery_level = progress.get("mastery_level", 0)
                if mastery_level == 0:
                    mastery_counts["new"] += 1
                elif mastery_level == 1:
                    mastery_counts["learning"] += 1
                elif mastery_level == 2:
                    mastery_counts["review"] += 1
                else:
                    mastery_counts["mastered"] += 1
                
                attempts = progress.get("quiz_attempts", 0)
                correct = progress.get("quiz_correct", 0)
                total_attempts += attempts
                total_correct += correct
            
            # Add unstudied cards to "new"
            unstudied_cards = total_cards - cards_studied
            mastery_counts["new"] += unstudied_cards
            
            # Calculate average accuracy
            average_accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0
            
            # Get deck study time and last studied
            total_study_time_minutes = deck_data.get("total_study_time", 0) // 60  # Convert from seconds
            
            last_studied_str = deck_data.get("last_studied_at")
            last_studied_at = None
            if last_studied_str:
                try:
                    last_studied_at = datetime.fromisoformat(last_studied_str.replace('Z', '+00:00'))
                except Exception:
                    pass
            
            return DeckStats(
                deck_id=str(deck_id),
                deck_name=deck_data["name"],
                total_cards=total_cards,
                cards_studied=cards_studied,
                study_progress_percentage=study_progress_percentage,
                mastery_distribution=mastery_counts,
                average_accuracy=average_accuracy,
                total_study_time_minutes=total_study_time_minutes,
                last_studied_at=last_studied_at
            )
            
        except Exception as e:
            print(f"Error getting deck statistics: {e}")
            return None
    
    async def get_all_deck_statistics(self, user_id: uuid.UUID) -> List[DeckStats]:
        """Get statistics for all user decks"""
        
        try:
            # Get all user decks
            decks_response = self.supabase.table("decks").select("id, name").eq("user_id", str(user_id)).execute()
            
            deck_stats = []
            for deck in decks_response.data:
                stats = await self.get_deck_statistics(user_id, uuid.UUID(deck["id"]))
                if stats:
                    deck_stats.append(stats)
            
            return deck_stats
            
        except Exception as e:
            print(f"Error getting all deck statistics: {e}")
            return []
    
    async def get_difficult_cards(self, user_id: uuid.UUID, limit: int = 20) -> List[CardStats]:
        """Get cards that the user finds most difficult"""
        
        try:
            # Get all user progress, ordered by difficulty score (descending) and accuracy (ascending)
            progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).gte("quiz_attempts", 2).execute()
            
            # Calculate difficulty and get card details
            card_stats = []
            
            for progress in progress_response.data:
                card_id = progress["card_id"]
                
                # Get card details
                card_response = self.supabase.table("cards").select("*").eq("id", card_id).execute()
                
                if card_response.data:
                    card_data = card_response.data[0]
                    
                    quiz_attempts = progress.get("quiz_attempts", 0)
                    quiz_correct = progress.get("quiz_correct", 0)
                    accuracy_rate = quiz_correct / quiz_attempts if quiz_attempts > 0 else 0.0
                    
                    # Parse dates
                    first_studied = None
                    last_studied = None
                    
                    if progress.get("first_flipped_at"):
                        try:
                            first_studied = datetime.fromisoformat(progress["first_flipped_at"].replace('Z', '+00:00'))
                        except Exception:
                            pass
                    
                    if progress.get("last_quiz_attempt_at"):
                        try:
                            last_studied = datetime.fromisoformat(progress["last_quiz_attempt_at"].replace('Z', '+00:00'))
                        except Exception:
                            pass
                    
                    card_stat = CardStats(
                        card_id=card_id,
                        hanzi=card_data["hanzi"],
                        pinyin=card_data["pinyin"],
                        english=card_data["english"],
                        mastery_level=progress.get("mastery_level", 0),
                        difficulty_score=progress.get("difficulty_score", 1.0),
                        quiz_attempts=quiz_attempts,
                        quiz_correct=quiz_correct,
                        accuracy_rate=accuracy_rate,
                        first_studied=first_studied,
                        last_studied=last_studied,
                        study_time_seconds=progress.get("total_study_time", 0)
                    )
                    
                    card_stats.append(card_stat)
            
            # Sort by difficulty (low accuracy, high difficulty score)
            card_stats.sort(key=lambda x: (x.accuracy_rate, -x.difficulty_score))
            
            return card_stats[:limit]
            
        except Exception as e:
            print(f"Error getting difficult cards: {e}")
            return []
    
    async def get_learning_progress_over_time(self, user_id: uuid.UUID, days: int = 30) -> Dict[str, List]:
        """Get learning progress over the specified number of days"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get study sessions over the period
            sessions_response = self.supabase.table("study_sessions").select("*").eq("user_id", str(user_id)).gte("created_at", start_date.isoformat()).order("created_at").execute()
            
            # Group by date
            daily_stats = {}
            
            for session in sessions_response.data:
                try:
                    session_date = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00')).date()
                    date_str = session_date.isoformat()
                    
                    if date_str not in daily_stats:
                        daily_stats[date_str] = {
                            "sessions": 0,
                            "cards_studied": 0,
                            "correct_answers": 0,
                            "total_attempts": 0,
                            "study_time_minutes": 0
                        }
                    
                    daily_stats[date_str]["sessions"] += 1
                    daily_stats[date_str]["cards_studied"] += session.get("cards_studied", 0)
                    daily_stats[date_str]["correct_answers"] += session.get("correct_answers", 0)
                    daily_stats[date_str]["study_time_minutes"] += session.get("session_duration", 0)
                    
                    # Approximate total attempts (assuming roughly equal to cards studied for simplicity)
                    daily_stats[date_str]["total_attempts"] += session.get("cards_studied", 0)
                    
                except Exception:
                    continue
            
            # Convert to lists for charting
            dates = []
            sessions_count = []
            accuracy_rates = []
            study_times = []
            cards_studied = []
            
            # Fill in all days (including zero days)
            current_date = start_date.date()
            end_date = datetime.utcnow().date()
            
            while current_date <= end_date:
                date_str = current_date.isoformat()
                dates.append(date_str)
                
                if date_str in daily_stats:
                    stats = daily_stats[date_str]
                    sessions_count.append(stats["sessions"])
                    study_times.append(stats["study_time_minutes"])
                    cards_studied.append(stats["cards_studied"])
                    
                    # Calculate accuracy
                    if stats["total_attempts"] > 0:
                        accuracy = stats["correct_answers"] / stats["total_attempts"]
                        accuracy_rates.append(accuracy * 100)  # Convert to percentage
                    else:
                        accuracy_rates.append(0)
                else:
                    sessions_count.append(0)
                    accuracy_rates.append(0)
                    study_times.append(0)
                    cards_studied.append(0)
                
                current_date += timedelta(days=1)
            
            return {
                "dates": dates,
                "sessions": sessions_count,
                "accuracy_rates": accuracy_rates,
                "study_times": study_times,
                "cards_studied": cards_studied
            }
            
        except Exception as e:
            print(f"Error getting learning progress over time: {e}")
            return {
                "dates": [],
                "sessions": [],
                "accuracy_rates": [],
                "study_times": [],
                "cards_studied": []
            }
    
    async def _calculate_study_streak(self, user_id: uuid.UUID) -> int:
        """Calculate consecutive days of study"""
        
        try:
            # Get recent study sessions
            sessions_response = self.supabase.table("study_sessions").select("created_at").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
            
            if not sessions_response.data:
                return 0
            
            # Group sessions by date
            study_dates = set()
            
            for session in sessions_response.data:
                try:
                    session_date = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00')).date()
                    study_dates.add(session_date)
                except Exception:
                    continue
            
            if not study_dates:
                return 0
            
            # Calculate streak
            study_dates_list = sorted(list(study_dates), reverse=True)
            current_date = datetime.utcnow().date()
            
            streak = 0
            
            # Check if studied today or yesterday
            if current_date in study_dates_list:
                streak += 1
                check_date = current_date - timedelta(days=1)
            elif current_date - timedelta(days=1) in study_dates_list:
                streak += 1
                check_date = current_date - timedelta(days=2)
            else:
                return 0
            
            # Count consecutive days
            while check_date in study_dates_list:
                streak += 1
                check_date -= timedelta(days=1)
            
            return streak
            
        except Exception as e:
            print(f"Error calculating study streak: {e}")
            return 0
    
    async def update_user_statistics(
        self, 
        user_id: uuid.UUID, 
        additional_study_time_minutes: int = 0,
        additional_views: int = 0,
        additional_quiz_attempts: int = 0,
        additional_correct_answers: int = 0
    ) -> bool:
        """Update user statistics incrementally"""
        
        try:
            # Get current stats
            stats_response = self.supabase.table("user_statistics").select("*").eq("user_id", str(user_id)).execute()
            
            if stats_response.data:
                # Update existing
                current_stats = stats_response.data[0]
                
                update_data = {
                    "total_views": current_stats.get("total_views", 0) + additional_views,
                    "total_correct_answers": current_stats.get("total_correct_answers", 0) + additional_correct_answers,
                    "total_quiz_attempts": current_stats.get("total_quiz_attempts", 0) + additional_quiz_attempts,
                    "study_time_minutes": current_stats.get("study_time_minutes", 0) + additional_study_time_minutes
                }
                
                self.supabase.table("user_statistics").update(update_data).eq("user_id", str(user_id)).execute()
            else:
                # Create new
                insert_data = {
                    "user_id": str(user_id),
                    "total_views": additional_views,
                    "total_correct_answers": additional_correct_answers,
                    "total_quiz_attempts": additional_quiz_attempts,
                    "study_time_minutes": additional_study_time_minutes
                }
                
                self.supabase.table("user_statistics").insert(insert_data).execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating user statistics: {e}")
            return False