"""
Authentication dependencies for FastAPI
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.auth_service import AuthService, security
from app.core.database import get_supabase_client


async def get_auth_service() -> AuthService:
    """Dependency to get auth service"""
    supabase_client = get_supabase_client()
    return AuthService(supabase_client)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Dependency to get current authenticated user"""
    return await auth_service.get_current_user(credentials)


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Dependency to get current active user"""
    # In a more complex app, you might check if user is disabled/inactive
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Dependency to get current user, but make it optional"""
    if not credentials:
        return None
    
    try:
        return auth_service.get_current_user(credentials)
    except HTTPException:
        return None