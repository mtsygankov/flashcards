"""
Authentication routes for login, logout, and registration
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.auth_service import AuthService
from app.auth.dependencies import get_auth_service, security
from app.schemas.schemas import (
    LoginRequest, 
    UserCreate, 
    UserResponse, 
    Token
)
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    # Check if username already exists
    existing_user = await auth_service.supabase.table("users").select("username").eq("username", user_data.username).execute()
    
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await auth_service.supabase.table("users").select("email").eq("email", user_data.email).execute()
    
    if existing_email.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await auth_service.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user"
        )
    
    return UserResponse(**user)


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login user and return access token"""
    user = await auth_service.authenticate_user(
        username=login_data.username,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user["username"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    # Set HTTP-only cookie (optional, for enhanced security)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        secure=settings.environment == "production"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user"""
    # Clear the cookie
    response.delete_cookie("access_token")
    
    # Sign out from Supabase
    await auth_service.logout_user()
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current user information"""
    user = await auth_service.get_current_user(credentials)
    return UserResponse(**user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token"""
    user = await auth_service.get_current_user(credentials)
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user["username"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}