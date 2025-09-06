"""
Study session service for managing learning sessions and progress tracking
"""
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from supabase import Client

from app.services.learning_service import LearningAlgorithm
from app.services.card_service import CardService
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


class StudySessionService:
    """Service for managing study sessions"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.learning_algorithm = LearningAlgorithm(supabase_client)
        self.card_service = CardService(supabase_client)
    
    async def create_study_session(
        self, 
        user_id: uuid.UUID, 
        session_create: StudySessionCreate
    ) -> Optional[StudySessionResponse]:
        """Create a new study session"""
        
        try:
            session_data = {
                "user_id": str(user_id),
                "deck_id": str(session_create.deck_id),
                "direction": session_create.direction,
                "cards_studied": 0,
                "correct_answers": 0,
                "session_duration": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("study_sessions").insert(session_data).execute()
            
            if response.data:
                return StudySessionResponse(**response.data[0])
            
            return None
            
        except Exception as e:
            print(f"Error creating study session: {e}")
            return None
    
    async def get_study_session(
        self, 
        session_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[StudySessionResponse]:
        """Get study session by ID"""
        
        try:
            response = self.supabase.table("study_sessions").select("*").eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if response.data:
                return StudySessionResponse(**response.data[0])
            
            return None
            
        except Exception as e:
            print(f"Error getting study session: {e}")
            return None
    
    async def update_study_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        session_update: StudySessionUpdate
    ) -> Optional[StudySessionResponse]:
        """Update study session progress"""
        
        try:
            update_data = session_update.dict(exclude_unset=True)
            
            if update_data:
                response = self.supabase.table("study_sessions").update(update_data).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
                
                if response.data:
                    return StudySessionResponse(**response.data[0])
            
            return await self.get_study_session(session_id, user_id)
            
        except Exception as e:
            print(f"Error updating study session: {e}")
            return None
    
    async def end_study_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        final_duration_minutes: int
    ) -> Optional[StudySessionResponse]:
        """End a study session and update final statistics"""
        
        try:
            # Get current session data
            session = await self.get_study_session(session_id, user_id)
            if not session:
                return None
            
            # Update session with final data
            update_data = {
                "session_duration": final_duration_minutes
            }
            
            response = self.supabase.table("study_sessions").update(update_data).eq("id", str(session_id)).eq("user_id", str(user_id)).execute()
            
            if response.data:
                # Update deck study time
                from app.services.deck_service import DeckService
                deck_service = DeckService(self.supabase)
                await deck_service.update_deck_study_time(
                    session.deck_id, 
                    final_duration_minutes * 60  # Convert to seconds
                )
                
                return StudySessionResponse(**response.data[0])
            
            return None
            
        except Exception as e:
            print(f"Error ending study session: {e}")
            return None
    
    async def get_study_cards(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        count: int = 10
    ) -> List[CardWithProgress]:
        """Get cards for study session using adaptive algorithm"""
        
        try:
            # Get session info
            session = await self.get_study_session(session_id, user_id)
            if not session:
                return []
            
            # Use learning algorithm to select cards
            selected_card_ids = await self.learning_algorithm.select_cards_for_study(
                user_id=user_id,
                deck_id=session.deck_id,
                target_count=count
            )
            
            # Get full card data with progress
            cards = []
            for card_id in selected_card_ids:
                card = await self.card_service.get_card_with_progress(
                    uuid.UUID(card_id), user_id
                )
                if card:
                    cards.append(card)
            
            return cards
            
        except Exception as e:
            print(f"Error getting study cards: {e}")
            return []
    
    async def record_card_interaction(
        self,
        interaction: CardInteractionCreate,
        user_id: uuid.UUID
    ) -> Optional[CardInteractionResponse]:
        """Record a card interaction during study session"""
        
        try:
            interaction_data = {
                "session_id": str(interaction.session_id),
                "user_id": str(user_id),
                "card_id": str(interaction.card_id),
                "interaction_type": interaction.interaction_type,
                "direction": interaction.direction,
                "response_time": interaction.response_time,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("card_interactions").insert(interaction_data).execute()
            
            if response.data:
                # Update user card progress using learning algorithm
                is_correct = None
                if interaction.interaction_type in ["quiz_correct", "quiz_incorrect"]:
                    is_correct = interaction.interaction_type == "quiz_correct"
                
                await self.learning_algorithm.update_card_progress(
                    user_id=user_id,
                    card_id=interaction.card_id,
                    interaction_type=interaction.interaction_type,
                    is_correct=is_correct,
                    response_time=interaction.response_time
                )
                
                return CardInteractionResponse(**response.data[0])
            
            return None
            
        except Exception as e:
            print(f"Error recording card interaction: {e}")
            return None
    
    async def generate_quiz_question(
        self,
        card_id: uuid.UUID,
        deck_id: uuid.UUID,
        direction: str,
        user_id: uuid.UUID
    ) -> Optional[QuizQuestionResponse]:
        """Generate a multiple choice quiz question"""
        
        try:
            # Get the target card
            target_card = await self.card_service.get_card_by_id(card_id)
            if not target_card:
                return None
            
            # Get other cards from the same deck for incorrect options
            deck_cards = await self.card_service.get_deck_cards(deck_id)
            other_cards = [card for card in deck_cards if card.id != card_id]
            
            if len(other_cards) < 3:
                # Not enough cards for multiple choice, return simple question
                if direction == "chinese_to_english":
                    question = f"What does '{target_card.hanzi}' ({target_card.pinyin}) mean?"
                    correct_answer = target_card.english
                else:
                    question = f"How do you say '{target_card.english}' in Chinese?"
                    correct_answer = f"{target_card.hanzi} ({target_card.pinyin})"
                
                return QuizQuestionResponse(
                    card_id=card_id,
                    question=question,
                    options=[correct_answer],
                    correct_answer=correct_answer,
                    direction=direction
                )
            
            # Generate multiple choice options
            if direction == "chinese_to_english":
                question = f"What does '{target_card.hanzi}' ({target_card.pinyin}) mean?"
                correct_answer = target_card.english
                
                # Get 3 random incorrect options
                incorrect_options = random.sample(other_cards, min(3, len(other_cards)))
                options = [correct_answer] + [card.english for card in incorrect_options]
                
            else:  # english_to_chinese
                question = f"How do you say '{target_card.english}' in Chinese?"
                correct_answer = f"{target_card.hanzi} ({target_card.pinyin})"
                
                # Get 3 random incorrect options
                incorrect_options = random.sample(other_cards, min(3, len(other_cards)))
                options = [correct_answer] + [f"{card.hanzi} ({card.pinyin})" for card in incorrect_options]
            
            # Shuffle options
            random.shuffle(options)
            
            return QuizQuestionResponse(
                card_id=card_id,
                question=question,
                options=options,
                correct_answer=correct_answer,
                direction=direction
            )
            
        except Exception as e:
            print(f"Error generating quiz question: {e}")
            return None
    
    async def submit_quiz_answer(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        answer: QuizAnswerRequest
    ) -> Optional[QuizAnswerResponse]:
        """Submit and evaluate a quiz answer"""
        
        try:
            # Get the correct answer by regenerating the question
            session = await self.get_study_session(session_id, user_id)
            if not session:
                return None
            
            question = await self.generate_quiz_question(
                card_id=answer.card_id,
                deck_id=session.deck_id,
                direction=session.direction,
                user_id=user_id
            )
            
            if not question:
                return None
            
            # Check if answer is correct
            is_correct = answer.selected_answer.strip().lower() == question.correct_answer.strip().lower()
            
            # Record the interaction
            interaction = CardInteractionCreate(
                session_id=session_id,
                card_id=answer.card_id,
                interaction_type="quiz_correct" if is_correct else "quiz_incorrect",
                direction=session.direction,
                response_time=answer.response_time
            )
            
            await self.record_card_interaction(interaction, user_id)
            
            # Update session statistics
            current_session = await self.get_study_session(session_id, user_id)
            if current_session:
                update_data = StudySessionUpdate(
                    cards_studied=current_session.cards_studied + 1,
                    correct_answers=current_session.correct_answers + (1 if is_correct else 0)
                )
                await self.update_study_session(session_id, user_id, update_data)
            
            # Generate explanation
            explanation = None
            if not is_correct:
                card = await self.card_service.get_card_by_id(answer.card_id)
                if card:
                    if session.direction == "chinese_to_english":
                        explanation = f"'{card.hanzi}' ({card.pinyin}) means '{card.english}'"
                    else:
                        explanation = f"'{card.english}' is '{card.hanzi}' ({card.pinyin}) in Chinese"
            
            return QuizAnswerResponse(
                correct=is_correct,
                correct_answer=question.correct_answer,
                explanation=explanation
            )
            
        except Exception as e:
            print(f"Error submitting quiz answer: {e}")
            return None
    
    async def get_user_study_sessions(
        self,
        user_id: uuid.UUID,
        deck_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[StudySessionResponse]:
        """Get user's study sessions"""
        
        try:
            query = self.supabase.table("study_sessions").select("*").eq("user_id", str(user_id))
            
            if deck_id:
                query = query.eq("deck_id", str(deck_id))
            
            query = query.order("created_at", desc=True).limit(limit)
            
            response = query.execute()
            
            return [StudySessionResponse(**session) for session in response.data]
            
        except Exception as e:
            print(f"Error getting user study sessions: {e}")
            return []
    
    async def get_session_statistics(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get detailed statistics for a study session"""
        
        try:
            # Get session data
            session = await self.get_study_session(session_id, user_id)
            if not session:
                return {}
            
            # Get all interactions for this session
            interactions_response = self.supabase.table("card_interactions").select("*").eq("session_id", str(session_id)).execute()
            
            interactions = interactions_response.data
            
            # Calculate statistics
            total_interactions = len(interactions)
            flip_count = len([i for i in interactions if i["interaction_type"] == "flip"])
            quiz_interactions = [i for i in interactions if i["interaction_type"].startswith("quiz_")]
            quiz_correct = len([i for i in quiz_interactions if i["interaction_type"] == "quiz_correct"])
            quiz_total = len(quiz_interactions)
            
            # Calculate average response time for quiz questions
            quiz_times = [i["response_time"] for i in quiz_interactions if i["response_time"]]
            avg_response_time = sum(quiz_times) / len(quiz_times) if quiz_times else 0
            
            # Cards studied
            unique_cards = set(i["card_id"] for i in interactions)
            cards_studied = len(unique_cards)
            
            return {
                "session_id": str(session_id),
                "total_interactions": total_interactions,
                "cards_flipped": flip_count,
                "quiz_questions": quiz_total,
                "quiz_correct": quiz_correct,
                "quiz_accuracy": quiz_correct / quiz_total if quiz_total > 0 else 0,
                "unique_cards_studied": cards_studied,
                "average_response_time_ms": avg_response_time,
                "session_duration_minutes": session.session_duration,
                "direction": session.direction,
                "created_at": session.created_at
            }
            
        except Exception as e:
            print(f"Error getting session statistics: {e}")
            return {}