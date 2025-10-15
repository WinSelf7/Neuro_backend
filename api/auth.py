"""
Authentication endpoints and utilities
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional
from database import get_db
from api import crud, schemas, models

router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error= False  # Allow bcrypt to auto-truncate >72 bytes
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password (bcrypt auto-truncates at 72 bytes)"""
    return pwd_context.hash(password)

# Request/Response Models
class SignupRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None

class SigninRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None

@router.post("/signup", response_model=AuthResponse)
async def signup(
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    try:
        # Debug logging
        print(f"=== BACKEND SIGNUP DEBUG ===")
        print(f"Username: {signup_data.username}")
        print(f"Password length: {len(signup_data.password)}")
        print(f"Password bytes length: {len(signup_data.password.encode('utf-8'))}")
        print(f"Email: {signup_data.email}")
        print(f"============================")
        
        # Check if username already exists
        existing_user = await crud.get_user_by_username(db, signup_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = await crud.get_user_by_email(db, signup_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Construct full name from first and last name if provided
        full_name = signup_data.full_name
        if not full_name and (signup_data.first_name or signup_data.last_name):
            full_name = f"{signup_data.first_name or ''} {signup_data.last_name or ''}".strip()
        
        # Create user
        user_create = schemas.UserCreate(
            username=signup_data.username,
            password=signup_data.password,
            email=signup_data.email,
            full_name=full_name
        )
        
        new_user = await crud.create_user(db, user_create)
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            user={
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.post("/signin", response_model=AuthResponse)
async def signin(
    signin_data: SigninRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user
    """
    try:
        # Get user by username
        user = await crud.get_user_by_username(db, signin_data.username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(signin_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return AuthResponse(
            success=True,
            message="Login successful",
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_superuser": user.is_superuser,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information
    """
    user = await crud.get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

