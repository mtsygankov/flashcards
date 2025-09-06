"""
Adaptive learning algorithm service for flashcard scheduling and difficulty management
"""
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from supabase import Client

from app.schemas.schemas import CardWithProgress, UserCardProgressResponse


@dataclass
class LearningConfig:
    """Configuration for the learning algorithm"""
    # Mastery level thresholds
    mastery_quiz_attempts_threshold: int = 5
    mastery_accuracy_threshold: float = 0.8
    review_accuracy_threshold: float = 0.6
    learning_accuracy_threshold: float = 0.4
    
    # Difficulty score parameters
    difficulty_increase_factor: float = 1.4
    difficulty_decrease_factor: float = 0.85
    min_difficulty_score: float = 0.1
    max_difficulty_score: float = 5.0
    
    # Review intervals (in hours)
    new_card_interval: int = 1
    learning_base_interval: int = 6
    review_base_interval: int = 24
    mastered_base_interval: int = 168  # 1 week
    
    # Selection weights
    new_card_weight: float = 2.0
    overdue_weight: float = 1.5
    learning_weight: float = 1.2
    review_weight: float = 1.0
    mastered_weight: float = 0.3


class LearningAlgorithm:
    """Adaptive learning algorithm for flashcard scheduling"""
    
    def __init__(self, supabase_client: Client, config: Optional[LearningConfig] = None):
        self.supabase = supabase_client
        self.config = config or LearningConfig()
    
    async def update_card_progress(
        self, 
        user_id: uuid.UUID, 
        card_id: uuid.UUID, 
        interaction_type: str, 
        is_correct: Optional[bool] = None,
        response_time: Optional[int] = None
    ) -> Optional[UserCardProgressResponse]:
        """Update user progress for a card based on interaction"""
        
        try:
            # Get existing progress or create new
            progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).eq("card_id", str(card_id)).execute()
            
            now = datetime.utcnow()
            
            if progress_response.data:
                # Update existing progress
                progress_data = progress_response.data[0]
                progress_id = progress_data["id"]
                
                # Update based on interaction type
                if interaction_type == "flip":
                    update_data = {
                        "flip_count": progress_data["flip_count"] + 1,
                        "last_flipped_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    }
                    
                    if not progress_data["first_flipped_at"]:
                        update_data["first_flipped_at"] = now.isoformat()
                
                elif interaction_type in ["quiz_correct", "quiz_incorrect"]:
                    is_correct = interaction_type == "quiz_correct"
                    
                    new_attempts = progress_data["quiz_attempts"] + 1
                    new_correct = progress_data["quiz_correct"] + (1 if is_correct else 0)
                    
                    # Calculate new difficulty score
                    new_difficulty = self._calculate_difficulty_score(
                        current_score=progress_data["difficulty_score"],
                        is_correct=is_correct,
                        consecutive_correct=progress_data["consecutive_correct"]
                    )
                    
                    # Calculate new mastery level
                    new_mastery_level = self._calculate_mastery_level(
                        quiz_attempts=new_attempts,
                        quiz_correct=new_correct,
                        current_level=progress_data["mastery_level"]
                    )
                    
                    # Calculate next review time
                    next_review = self._calculate_next_review_time(
                        mastery_level=new_mastery_level,
                        difficulty_score=new_difficulty,
                        is_correct=is_correct
                    )
                    
                    update_data = {
                        "quiz_attempts": new_attempts,
                        "quiz_correct": new_correct,
                        "last_quiz_attempt_at": now.isoformat(),
                        "difficulty_score": new_difficulty,
                        "mastery_level": new_mastery_level,
                        "next_review_at": next_review.isoformat(),
                        "consecutive_correct": progress_data["consecutive_correct"] + 1 if is_correct else 0,
                        "updated_at": now.isoformat()
                    }
                
                # Update the record
                update_response = self.supabase.table("user_card_progress").update(update_data).eq("id", progress_id).execute()
                
                if update_response.data:
                    return UserCardProgressResponse(**update_response.data[0])
            
            else:
                # Create new progress record
                if interaction_type == "flip":
                    progress_data = {
                        "user_id": str(user_id),
                        "card_id": str(card_id),
                        "flip_count": 1,
                        "first_flipped_at": now.isoformat(),
                        "last_flipped_at": now.isoformat(),
                        "quiz_attempts": 0,
                        "quiz_correct": 0,
                        "difficulty_score": 1.0,
                        "mastery_level": 0,
                        "next_review_at": now.isoformat(),
                        "consecutive_correct": 0,
                        "total_study_time": 0,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    }
                
                elif interaction_type in ["quiz_correct", "quiz_incorrect"]:
                    is_correct = interaction_type == "quiz_correct"
                    
                    difficulty_score = self._calculate_difficulty_score(1.0, is_correct, 0)
                    mastery_level = self._calculate_mastery_level(1, 1 if is_correct else 0, 0)
                    next_review = self._calculate_next_review_time(mastery_level, difficulty_score, is_correct)
                    
                    progress_data = {
                        "user_id": str(user_id),
                        "card_id": str(card_id),
                        "flip_count": 0,
                        "quiz_attempts": 1,
                        "quiz_correct": 1 if is_correct else 0,
                        "last_quiz_attempt_at": now.isoformat(),
                        "difficulty_score": difficulty_score,
                        "mastery_level": mastery_level,
                        "next_review_at": next_review.isoformat(),
                        "consecutive_correct": 1 if is_correct else 0,
                        "total_study_time": 0,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat()
                    }
                
                # Insert new record
                insert_response = self.supabase.table("user_card_progress").insert(progress_data).execute()
                
                if insert_response.data:
                    return UserCardProgressResponse(**insert_response.data[0])
            
            return None
            
        except Exception as e:
            print(f"Error updating card progress: {e}")
            return None
    
    def _calculate_difficulty_score(
        self, 
        current_score: float, 
        is_correct: bool, 
        consecutive_correct: int
    ) -> float:
        """Calculate new difficulty score based on performance"""
        
        if is_correct:
            # Decrease difficulty for correct answers
            new_score = current_score * self.config.difficulty_decrease_factor
            
            # Additional decrease for consecutive correct answers
            if consecutive_correct >= 3:
                new_score *= 0.9
        else:
            # Increase difficulty for incorrect answers
            new_score = current_score * self.config.difficulty_increase_factor
        
        # Clamp to valid range
        return max(
            self.config.min_difficulty_score,
            min(self.config.max_difficulty_score, new_score)
        )
    
    def _calculate_mastery_level(
        self, 
        quiz_attempts: int, 
        quiz_correct: int, 
        current_level: int
    ) -> int:
        """Calculate mastery level based on performance"""
        
        if quiz_attempts == 0:
            return 0  # New
        
        accuracy = quiz_correct / quiz_attempts
        
        # Determine mastery level based on attempts and accuracy
        if (quiz_attempts >= 10 and 
            accuracy >= self.config.mastery_accuracy_threshold):
            return 3  # Mastered
        elif (quiz_attempts >= self.config.mastery_quiz_attempts_threshold and 
              accuracy >= self.config.review_accuracy_threshold):
            return 2  # Review
        elif (quiz_attempts >= 2 and 
              accuracy >= self.config.learning_accuracy_threshold):
            return 1  # Learning
        else:
            return 0  # New/struggling
    
    def _calculate_next_review_time(
        self, 
        mastery_level: int, 
        difficulty_score: float, 
        is_correct: bool
    ) -> datetime:
        """Calculate when the card should next be reviewed"""
        
        now = datetime.utcnow()
        
        # Base intervals by mastery level
        if mastery_level == 0:  # New
            base_interval = self.config.new_card_interval
        elif mastery_level == 1:  # Learning
            base_interval = self.config.learning_base_interval
        elif mastery_level == 2:  # Review
            base_interval = self.config.review_base_interval
        else:  # Mastered
            base_interval = self.config.mastered_base_interval
        
        # Adjust interval based on difficulty and correctness
        if is_correct:
            # Increase interval for correct answers
            interval_multiplier = 1.0 / difficulty_score
        else:
            # Decrease interval for incorrect answers
            interval_multiplier = difficulty_score * 0.5
        
        final_interval = base_interval * interval_multiplier
        
        # Clamp interval to reasonable bounds
        final_interval = max(0.5, min(720, final_interval))  # 30 min to 30 days
        
        return now + timedelta(hours=final_interval)
    
    async def select_cards_for_study(
        self, 
        user_id: uuid.UUID, 
        deck_id: uuid.UUID, 
        target_count: int = 10,
        include_overdue: bool = True
    ) -> List[uuid.UUID]:
        """Select cards for study session using adaptive algorithm"""
        
        try:
            # Get all cards in the deck
            cards_response = self.supabase.table("cards").select("id").eq("deck_id", str(deck_id)).execute()
            
            if not cards_response.data:
                return []
            
            card_ids = [card["id"] for card in cards_response.data]
            
            # Get user progress for all cards
            card_priorities = []
            now = datetime.utcnow()
            
            for card_id in card_ids:
                progress_response = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id)).eq("card_id", card_id).execute()
                
                if progress_response.data:
                    progress = progress_response.data[0]
                    
                    # Calculate priority score
                    priority = self._calculate_card_priority(progress, now, include_overdue)
                else:
                    # New card - high priority
                    priority = self.config.new_card_weight * 2.0
                
                card_priorities.append((card_id, priority))
            
            # Sort by priority (higher is better)
            card_priorities.sort(key=lambda x: x[1], reverse=True)
            
            # Select top cards, with some randomization to avoid predictability
            selected_count = min(target_count, len(card_priorities))
            
            if selected_count <= target_count // 2:
                # If we have few cards, select deterministically
                selected_cards = [card_id for card_id, _ in card_priorities[:selected_count]]
            else:
                # Use weighted selection for variety
                selected_cards = self._weighted_selection(card_priorities, selected_count)
            
            return selected_cards
            
        except Exception as e:
            print(f"Error selecting cards for study: {e}")
            return card_ids[:target_count] if card_ids else []
    
    def _calculate_card_priority(
        self, 
        progress: Dict, 
        current_time: datetime, 
        include_overdue: bool
    ) -> float:
        """Calculate priority score for a card"""
        
        mastery_level = progress.get("mastery_level", 0)
        difficulty_score = progress.get("difficulty_score", 1.0)
        next_review_str = progress.get("next_review_at")
        
        # Base priority by mastery level
        if mastery_level == 0:  # New
            base_priority = self.config.new_card_weight
        elif mastery_level == 1:  # Learning
            base_priority = self.config.learning_weight
        elif mastery_level == 2:  # Review
            base_priority = self.config.review_weight
        else:  # Mastered
            base_priority = self.config.mastered_weight
        
        # Adjust by difficulty
        priority = base_priority * difficulty_score
        
        # Boost overdue cards
        if include_overdue and next_review_str:
            try:
                next_review = datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
                if next_review <= current_time:
                    # Card is overdue
                    overdue_hours = (current_time - next_review).total_seconds() / 3600
                    overdue_multiplier = 1.0 + min(overdue_hours / 24, 2.0)  # Max 3x boost
                    priority *= overdue_multiplier * self.config.overdue_weight
            except Exception:
                pass
        
        return priority
    
    def _weighted_selection(
        self, 
        card_priorities: List[Tuple[str, float]], 
        count: int
    ) -> List[str]:
        """Select cards using weighted random selection"""
        
        # Take top candidates (2x the target count)
        candidates = card_priorities[:count * 2]
        
        if len(candidates) <= count:
            return [card_id for card_id, _ in candidates]
        
        # Extract weights
        card_ids = [card_id for card_id, _ in candidates]
        weights = [priority for _, priority in candidates]
        
        # Weighted random selection without replacement
        selected = []
        remaining_ids = card_ids[:]
        remaining_weights = weights[:]
        
        for _ in range(count):
            if not remaining_ids:
                break
            
            # Select based on weights
            selected_idx = random.choices(range(len(remaining_ids)), weights=remaining_weights)[0]
            selected.append(remaining_ids[selected_idx])
            
            # Remove selected card
            remaining_ids.pop(selected_idx)
            remaining_weights.pop(selected_idx)
        
        return selected
    
    async def get_study_statistics(self, user_id: uuid.UUID, deck_id: Optional[uuid.UUID] = None) -> Dict:
        """Get study statistics for adaptive algorithm tuning"""
        
        try:
            query = self.supabase.table("user_card_progress").select("*").eq("user_id", str(user_id))
            
            if deck_id:
                # Filter by deck - need to join with cards table
                cards_response = self.supabase.table("cards").select("id").eq("deck_id", str(deck_id)).execute()
                
                if cards_response.data:
                    card_ids = [card["id"] for card in cards_response.data]
                    query = query.in_("card_id", card_ids)
                else:
                    return {}
            
            progress_response = query.execute()
            
            if not progress_response.data:
                return {}
            
            # Calculate statistics
            total_cards = len(progress_response.data)
            mastery_counts = {0: 0, 1: 0, 2: 0, 3: 0}
            total_attempts = 0
            total_correct = 0
            avg_difficulty = 0.0
            overdue_count = 0
            
            now = datetime.utcnow()
            
            for progress in progress_response.data:
                mastery_level = progress.get("mastery_level", 0)
                mastery_counts[mastery_level] += 1
                
                attempts = progress.get("quiz_attempts", 0)
                correct = progress.get("quiz_correct", 0)
                total_attempts += attempts
                total_correct += correct
                
                difficulty = progress.get("difficulty_score", 1.0)
                avg_difficulty += difficulty
                
                # Check if overdue
                next_review_str = progress.get("next_review_at")
                if next_review_str:
                    try:
                        next_review = datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
                        if next_review <= now:
                            overdue_count += 1
                    except Exception:
                        pass
            
            avg_difficulty = avg_difficulty / total_cards if total_cards > 0 else 0.0
            overall_accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0
            
            return {
                "total_cards": total_cards,
                "mastery_distribution": {
                    "new": mastery_counts[0],
                    "learning": mastery_counts[1],
                    "review": mastery_counts[2],
                    "mastered": mastery_counts[3]
                },
                "overall_accuracy": overall_accuracy,
                "average_difficulty": avg_difficulty,
                "overdue_cards": overdue_count,
                "total_attempts": total_attempts,
                "total_correct": total_correct
            }
            
        except Exception as e:
            print(f"Error getting study statistics: {e}")
            return {}