from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.session import get_db
from app.schemas.user import (
    UserLoginRequest,
    UserRegisterRequest,
    LoginResponse,
    Msg,
    APIResponse,
)
from app.models.user import User
from app.crud import user as crud_user
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    responses={
        401: {"model": APIResponse, "description": "Invalid credentials"},
        404: {"model": APIResponse, "description": "User not found"},
    }
)
async def login(
    login_request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.
    
    Accepts either username or email with password.
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: Always "bearer"
    - **user**: User information with role
    
    Example request:
    ```json
    {
        "login": "admin@example.com",
        "password": "password123"
    }
    ```
    """
    # Authenticate user
    user = crud_user.authenticate_user(
        db,
        login=login_request.login,
        password=login_request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    
    # Create access token
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    responses={
        400: {"model": APIResponse, "description": "User already exists"},
    }
)
async def register(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    User registration endpoint.
    
    Creates a new user account.
    
    Example request:
    ```json
    {
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "password123",
        "role": "user"
    }
    ```
    """
    # Check if user already exists
    existing_user = crud_user.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    existing_user = crud_user.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Create user
    new_user = crud_user.create_user(db, user_data)
    
    # Create access token
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        subject=str(new_user.id),
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user,
    }


@router.get(
    "/health",
    response_model=Msg,
    tags=["Health"],
)
async def health_check():
    """
    Health check endpoint.
    
    Returns status of the API.
    """
    return {"message": "API is running"}
