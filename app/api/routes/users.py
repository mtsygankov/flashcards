"""
User management API routes
"""
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.user_service import UserService
from app.auth.dependencies import get_current_active_user, get_optional_current_user
from app.core.database import get_supabase_client
from app.schemas.schemas import (
    UserResponse, 
    UserUpdate, 
    UserStatisticsResponse
)

router = APIRouter(prefix="/users", tags=["users"])


async def get_user_service() -> UserService:
    """Dependency to get user service"""
    supabase_client = get_supabase_client()
    return UserService(supabase_client)


@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    user_service: UserService = Depends(get_user_service)
):
    """Get all users - public endpoint for user selection"""
    return await user_service.get_all_users()


@router.get("/with-stats")
async def get_users_with_statistics(
    user_service: UserService = Depends(get_user_service)
):
    """Get all users with their statistics for user selection page"""
    return await user_service.get_users_with_stats()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_active_user)
):
    """Get current user's profile"""
    return UserResponse(**current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID"""
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's profile"""
    updated_user = await user_service.update_user(
        uuid.UUID(current_user["id"]), 
        user_update
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update user"
        )
    
    return updated_user


@router.delete("/me")
async def delete_current_user(
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Delete current user's account"""
    success = await user_service.delete_user(uuid.UUID(current_user["id"]))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete user"
        )
    
    return {"message": "User deleted successfully"}


@router.get("/me/statistics", response_model=UserStatisticsResponse)
async def get_current_user_statistics(
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's statistics"""
    stats = await user_service.get_user_statistics(uuid.UUID(current_user["id"]))
    
    if not stats:
        # Create default statistics if none exist
        return UserStatisticsResponse(
            total_views=0,
            total_correct_answers=0,
            total_quiz_attempts=0,
            study_time_minutes=0
        )
    
    return stats


@router.get("/{user_id}/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service)
):
    """Get user statistics by ID - public for user selection"""
    stats = await user_service.get_user_statistics(user_id)
    
    if not stats:
        return UserStatisticsResponse(
            total_views=0,
            total_correct_answers=0,
            total_quiz_attempts=0,
            study_time_minutes=0
        )
    
    return stats


@router.post("/select/{user_id}")
async def select_user(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service)
):
    """Select a user for the session (updates last_active)"""
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update last active timestamp
    await user_service.update_last_active(user_id)
    
    return {
        "message": "User selected successfully",
        "user": user
    }