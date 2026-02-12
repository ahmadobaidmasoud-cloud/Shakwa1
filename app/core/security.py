import bcrypt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt with SHA256 pre-hashing to avoid bcrypt 72-byte limit"""
    sha256 = hashlib.sha256(password.encode("utf-8")).digest()
    hashed = bcrypt.hashpw(sha256, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    sha256 = hashlib.sha256(password.encode("utf-8")).digest()
    return bcrypt.checkpw(sha256, hashed_password.encode("utf-8"))


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """Create JWT refresh token"""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_access_token(subject=subject, expires_delta=expires_delta)
