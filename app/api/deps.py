from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.db.session import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.user import TokenPayload
from app.crud import user as crud_user

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = crud_user.get_user_by_id(db, UUID(token_data.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


def get_current_Super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Get current super-admin user"""
    logger.debug(f"Role check for user {current_user.id}: role={current_user.role}, type={type(current_user.role)}")
    
    # Check if user has super-admin role
    is_super_admin = (
        current_user.role == UserRole.super_admin or
        (hasattr(current_user.role, 'value') and current_user.role.value == "super-admin") or
        str(current_user.role) == "super-admin"
    )
    
    if not is_super_admin:
        logger.warning(f"Unauthorized super-admin access attempt by user {current_user.id} with role {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Super Admin access required. Your role: {current_user.role}",
        )
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Get current admin user"""
    # Check role value (handles both enum and string comparisons)
    role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role_value not in ["admin", "super-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required.",
        )
    return current_user
