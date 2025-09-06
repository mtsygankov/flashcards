"""
Authentication utilities using Supabase Auth
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from supabase import Client

from app.core.config import get_settings
from app.schemas.schemas import TokenData

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class AuthService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with username/password using Supabase"""
        try:
            # First try to get user by username from our users table
            response = self.supabase.table("users").select("*").eq("username", username).execute()
            
            if not response.data:
                return None
            
            user_data = response.data[0]
            
            # For development, we'll use a simple password check
            # In production, you'd want proper password hashing
            # This is a simplified implementation
            
            # Try to sign in with Supabase Auth using email/password
            try:
                auth_response = self.supabase.auth.sign_in_with_password({
                    "email": user_data["email"],
                    "password": password
                })
                
                if auth_response.user:
                    # Update last_active_at
                    self.supabase.table("users").update({
                        "last_active_at": datetime.utcnow().isoformat()
                    }).eq("id", user_data["id"]).execute()
                    
                    return {
                        "id": user_data["id"],
                        "username": user_data["username"],
                        "email": user_data["email"],
                        "supabase_user_id": auth_response.user.id
                    }
            except Exception as e:
                print(f"Supabase auth error: {e}")
                return None
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """Get current user from JWT token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception
        
        # Get user from database
        response = self.supabase.table("users").select("*").eq("username", token_data.username).execute()
        
        if not response.data:
            raise credentials_exception
        
        return response.data[0]
    
    async def register_user(self, username: str, email: str, password: str) -> Optional[dict]:
        """Register a new user"""
        try:
            # First create user in Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if not auth_response.user:
                return None
            
            # Then create user record in our users table
            user_data = {
                "username": username,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "last_active_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table("users").insert(user_data).execute()
            
            if response.data:
                # Create user statistics record
                stats_data = {
                    "user_id": response.data[0]["id"]
                }
                self.supabase.table("user_statistics").insert(stats_data).execute()
                
                return response.data[0]
                
        except Exception as e:
            print(f"Registration error: {e}")
            return None
    
    async def logout_user(self) -> bool:
        """Logout user from Supabase"""
        try:
            self.supabase.auth.sign_out()
            return True
        except Exception as e:
            print(f"Logout error: {e}")
            return False