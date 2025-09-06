"""
Statistics API routes for analytics and progress tracking
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.services.statistics_service import StatisticsService, LearningStats, DeckStats, CardStats
from app.auth.dependencies import get_current_active_user
from app.core.database import get_supabase_client

router = APIRouter(prefix="/statistics", tags=["statistics"])


async def get_statistics_service() -> StatisticsService:
    """Dependency to get statistics service"""
    supabase_client = get_supabase_client()
    return StatisticsService(supabase_client)


@router.get("/overview")
async def get_user_overview_statistics(
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get overall learning statistics for the current user"""
    
    stats = await stats_service.get_user_overview_stats(
        user_id=uuid.UUID(current_user["id"])
    )
    
    return {
        "total_study_time_minutes": stats.total_study_time_minutes,
        "total_cards_studied": stats.total_cards_studied,
        "total_quiz_attempts": stats.total_quiz_attempts,
        "total_correct_answers": stats.total_correct_answers,
        "overall_accuracy": round(stats.overall_accuracy * 100, 1),  # Convert to percentage
        "study_streak_days": stats.study_streak_days,
        "cards_by_mastery": stats.cards_by_mastery,
        "recent_sessions_count": stats.recent_sessions_count,
        "average_session_duration": round(stats.average_session_duration, 1)
    }


@router.get("/decks/{deck_id}")
async def get_deck_statistics(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get statistics for a specific deck"""
    
    stats = await stats_service.get_deck_statistics(
        user_id=uuid.UUID(current_user["id"]),
        deck_id=deck_id
    )
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found or no statistics available"
        )
    
    return {
        "deck_id": stats.deck_id,
        "deck_name": stats.deck_name,
        "total_cards": stats.total_cards,
        "cards_studied": stats.cards_studied,
        "study_progress_percentage": round(stats.study_progress_percentage, 1),
        "mastery_distribution": stats.mastery_distribution,
        "average_accuracy": round(stats.average_accuracy * 100, 1),  # Convert to percentage
        "total_study_time_minutes": stats.total_study_time_minutes,
        "last_studied_at": stats.last_studied_at.isoformat() if stats.last_studied_at else None
    }


@router.get("/decks")
async def get_all_deck_statistics(
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get statistics for all user decks"""
    
    deck_stats_list = await stats_service.get_all_deck_statistics(
        user_id=uuid.UUID(current_user["id"])
    )
    
    return [
        {
            "deck_id": stats.deck_id,
            "deck_name": stats.deck_name,
            "total_cards": stats.total_cards,
            "cards_studied": stats.cards_studied,
            "study_progress_percentage": round(stats.study_progress_percentage, 1),
            "mastery_distribution": stats.mastery_distribution,
            "average_accuracy": round(stats.average_accuracy * 100, 1),
            "total_study_time_minutes": stats.total_study_time_minutes,
            "last_studied_at": stats.last_studied_at.isoformat() if stats.last_studied_at else None
        }
        for stats in deck_stats_list
    ]


@router.get("/difficult-cards")
async def get_difficult_cards(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get cards that the user finds most difficult"""
    
    difficult_cards = await stats_service.get_difficult_cards(
        user_id=uuid.UUID(current_user["id"]),
        limit=limit
    )
    
    return [
        {
            "card_id": card.card_id,
            "hanzi": card.hanzi,
            "pinyin": card.pinyin,
            "english": card.english,
            "mastery_level": card.mastery_level,
            "difficulty_score": round(card.difficulty_score, 2),
            "quiz_attempts": card.quiz_attempts,
            "quiz_correct": card.quiz_correct,
            "accuracy_rate": round(card.accuracy_rate * 100, 1),
            "first_studied": card.first_studied.isoformat() if card.first_studied else None,
            "last_studied": card.last_studied.isoformat() if card.last_studied else None,
            "study_time_seconds": card.study_time_seconds
        }
        for card in difficult_cards
    ]


@router.get("/progress-over-time")
async def get_learning_progress_over_time(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get learning progress over the specified number of days"""
    
    progress_data = await stats_service.get_learning_progress_over_time(
        user_id=uuid.UUID(current_user["id"]),
        days=days
    )
    
    return progress_data


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get comprehensive dashboard data"""
    
    user_id = uuid.UUID(current_user["id"])
    
    # Get overview statistics
    overview_stats = await stats_service.get_user_overview_stats(user_id)
    
    # Get deck statistics
    deck_stats = await stats_service.get_all_deck_statistics(user_id)
    
    # Get difficult cards (top 10)
    difficult_cards = await stats_service.get_difficult_cards(user_id, limit=10)
    
    # Get recent progress (last 7 days)
    recent_progress = await stats_service.get_learning_progress_over_time(user_id, days=7)
    
    return {
        "overview": {
            "total_study_time_minutes": overview_stats.total_study_time_minutes,
            "total_cards_studied": overview_stats.total_cards_studied,
            "total_quiz_attempts": overview_stats.total_quiz_attempts,
            "total_correct_answers": overview_stats.total_correct_answers,
            "overall_accuracy": round(overview_stats.overall_accuracy * 100, 1),
            "study_streak_days": overview_stats.study_streak_days,
            "cards_by_mastery": overview_stats.cards_by_mastery,
            "recent_sessions_count": overview_stats.recent_sessions_count,
            "average_session_duration": round(overview_stats.average_session_duration, 1)
        },
        "decks": [
            {
                "deck_id": stats.deck_id,
                "deck_name": stats.deck_name,
                "total_cards": stats.total_cards,
                "cards_studied": stats.cards_studied,
                "study_progress_percentage": round(stats.study_progress_percentage, 1),
                "mastery_distribution": stats.mastery_distribution,
                "average_accuracy": round(stats.average_accuracy * 100, 1),
                "total_study_time_minutes": stats.total_study_time_minutes
            }
            for stats in deck_stats
        ],
        "difficult_cards": [
            {
                "card_id": card.card_id,
                "hanzi": card.hanzi,
                "pinyin": card.pinyin,
                "english": card.english,
                "accuracy_rate": round(card.accuracy_rate * 100, 1),
                "difficulty_score": round(card.difficulty_score, 2)
            }
            for card in difficult_cards
        ],
        "recent_progress": recent_progress
    }


@router.post("/update")
async def update_user_statistics_manually(
    study_time_minutes: int = 0,
    views: int = 0,
    quiz_attempts: int = 0,
    correct_answers: int = 0,
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Manually update user statistics (for testing or corrections)"""
    
    success = await stats_service.update_user_statistics(
        user_id=uuid.UUID(current_user["id"]),
        additional_study_time_minutes=study_time_minutes,
        additional_views=views,
        additional_quiz_attempts=quiz_attempts,
        additional_correct_answers=correct_answers
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update statistics"
        )
    
    return {"message": "Statistics updated successfully"}


@router.get("/learning-algorithm")
async def get_learning_algorithm_statistics(
    deck_id: Optional[uuid.UUID] = None,
    current_user: dict = Depends(get_current_active_user),
    stats_service: StatisticsService = Depends(get_statistics_service)
):
    """Get statistics for tuning the learning algorithm"""
    
    from app.services.learning_service import LearningAlgorithm
    
    supabase_client = get_supabase_client()
    learning_algorithm = LearningAlgorithm(supabase_client)
    
    algorithm_stats = await learning_algorithm.get_study_statistics(
        user_id=uuid.UUID(current_user["id"]),
        deck_id=deck_id
    )
    
    return algorithm_stats