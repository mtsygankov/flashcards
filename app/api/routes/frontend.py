"""
Frontend routes for serving HTML pages with HTMX integration
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.services.user_service import UserService
from app.services.deck_service import DeckService
from app.services.study_service import StudySessionService
from app.services.statistics_service import StatisticsService
from app.auth.dependencies import get_current_active_user, get_optional_current_user
from app.core.database import get_supabase_client

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")


async def get_services():
    """Get all required services"""
    supabase_client = get_supabase_client()
    return {
        "user_service": UserService(supabase_client),
        "deck_service": DeckService(supabase_client),
        "study_service": StudySessionService(supabase_client),
        "stats_service": StatisticsService(supabase_client)
    }


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Home page"""
    if current_user:
        # Redirect to dashboard if already logged in
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "redirect_url": "/dashboard"
        })
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """User dashboard"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Get overview statistics
        stats = await services["stats_service"].get_user_overview_stats(user_id)
        
        # Get recent decks (limit to 5)
        recent_decks = await services["deck_service"].get_user_decks(user_id)
        recent_decks = recent_decks[:5]  # Limit to 5 most recent
        
        # Get progress data for chart (last 7 days)
        progress_data = await services["stats_service"].get_learning_progress_over_time(user_id, days=7)
        
        # Add progress percentage to decks
        for deck in recent_decks:
            deck_stats = await services["stats_service"].get_deck_statistics(user_id, deck.id)
            deck.progress_percentage = deck_stats.study_progress_percentage if deck_stats else 0.0
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "recent_decks": recent_decks,
            "progress_data": progress_data
        })
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not load dashboard data"
        })


@router.get("/decks", response_class=HTMLResponse)
async def decks_list(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """List user decks"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Get user decks with statistics
        decks = await services["deck_service"].get_user_decks(user_id)
        
        # Add statistics to each deck
        decks_with_stats = []
        for deck in decks:
            deck_stats = await services["stats_service"].get_deck_statistics(user_id, deck.id)
            deck_data = {
                "deck": deck,
                "stats": deck_stats
            }
            decks_with_stats.append(deck_data)
        
        return templates.TemplateResponse("decks/list.html", {
            "request": request,
            "current_user": current_user,
            "decks": decks_with_stats
        })
        
    except Exception as e:
        print(f"Error loading decks: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not load decks"
        })


@router.get("/decks/{deck_id}", response_class=HTMLResponse)
async def deck_detail(
    request: Request,
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_active_user)
):
    """Deck detail page"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Get deck information
        deck = await services["deck_service"].get_deck_by_id(deck_id, user_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        # Get deck statistics
        deck_stats = await services["stats_service"].get_deck_statistics(user_id, deck_id)
        
        # Get cards in the deck (with pagination)
        from app.services.card_service import CardService
        card_service = CardService(get_supabase_client())
        
        from app.schemas.schemas import PaginationParams
        pagination = PaginationParams(page=1, size=20)
        
        cards_result = await card_service.get_paginated_cards(deck_id, pagination)
        
        return templates.TemplateResponse("decks/detail.html", {
            "request": request,
            "current_user": current_user,
            "deck": deck,
            "deck_stats": deck_stats,
            "cards": cards_result.items,
            "pagination": {
                "current_page": cards_result.page,
                "total_pages": cards_result.pages,
                "total_cards": cards_result.total
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading deck detail: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not load deck details"
        })


@router.get("/study", response_class=HTMLResponse)
async def study_selection(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """Study deck selection page"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Get user decks for selection
        decks = await services["deck_service"].get_user_decks(user_id)
        
        # Add study readiness information
        study_ready_decks = []
        for deck in decks:
            if deck.card_count > 0:  # Only decks with cards
                deck_stats = await services["stats_service"].get_deck_statistics(user_id, deck.id)
                study_ready_decks.append({
                    "deck": deck,
                    "stats": deck_stats
                })
        
        return templates.TemplateResponse("study/selection.html", {
            "request": request,
            "current_user": current_user,
            "decks": study_ready_decks
        })
        
    except Exception as e:
        print(f"Error loading study selection: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not load study page"
        })


@router.get("/study/{deck_id}", response_class=HTMLResponse)
async def start_study_session(
    request: Request,
    deck_id: uuid.UUID,
    direction: str = "chinese_to_english",
    mode: str = "flip",
    card: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    """Start or continue study session"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Verify deck exists and belongs to user
        deck = await services["deck_service"].get_deck_by_id(deck_id, user_id)
        if not deck:
            raise HTTPException(status_code=404, detail="Deck not found")
        
        # Create or get study session
        from app.schemas.schemas import StudySessionCreate
        session_create = StudySessionCreate(deck_id=deck_id, direction=direction)
        session = await services["study_service"].create_study_session(user_id, session_create)
        
        if not session:
            raise HTTPException(status_code=400, detail="Could not create study session")
        
        # Get study cards using adaptive algorithm
        study_cards = await services["study_service"].get_study_cards(
            session.id, user_id, count=10
        )
        
        # Determine what to show based on mode and card index
        current_card_data = None
        quiz_question = None
        session_complete = False
        
        if card < len(study_cards):
            current_card_data = study_cards[card]
            
            if mode == "quiz":
                quiz_question = await services["study_service"].generate_quiz_question(
                    card_id=current_card_data.id,
                    deck_id=deck_id,
                    direction=direction,
                    user_id=user_id
                )
        elif card >= len(study_cards) and len(study_cards) > 0:
            session_complete = True
        
        # Get session statistics
        session_stats = await services["study_service"].get_session_statistics(session.id, user_id)
        
        # Direction text for display
        direction_text = "Chinese → English" if direction == "chinese_to_english" else "English → Chinese"
        
        # Mastery level names
        mastery_levels = {0: "New", 1: "Learning", 2: "Review", 3: "Mastered"}
        
        return templates.TemplateResponse("study.html", {
            "request": request,
            "current_user": current_user,
            "deck": deck,
            "session": session,
            "direction": direction,
            "direction_text": direction_text,
            "study_mode": mode,
            "current_card": card,
            "total_cards": len(study_cards),
            "current_card_data": current_card_data,
            "quiz_question": quiz_question,
            "session_complete": session_complete,
            "session_stats": session_stats,
            "mastery_levels": mastery_levels
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting study session: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not start study session"
        })


@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """Statistics and analytics page"""
    services = await get_services()
    user_id = uuid.UUID(current_user["id"])
    
    try:
        # Get comprehensive statistics
        overview_stats = await services["stats_service"].get_user_overview_stats(user_id)
        deck_stats = await services["stats_service"].get_all_deck_statistics(user_id)
        difficult_cards = await services["stats_service"].get_difficult_cards(user_id, limit=20)
        progress_data = await services["stats_service"].get_learning_progress_over_time(user_id, days=30)
        
        return templates.TemplateResponse("statistics.html", {
            "request": request,
            "current_user": current_user,
            "overview_stats": overview_stats,
            "deck_stats": deck_stats,
            "difficult_cards": difficult_cards,
            "progress_data": progress_data
        })
        
    except Exception as e:
        print(f"Error loading statistics: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Could not load statistics"
        })


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Login page"""
    if current_user:
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "redirect_url": "/dashboard"
        })
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Registration page"""
    if current_user:
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "redirect_url": "/dashboard"
        })
    
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/error", response_class=HTMLResponse)
async def error_page(
    request: Request,
    message: str = "An error occurred",
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Generic error page"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "current_user": current_user,
        "error": message
    })