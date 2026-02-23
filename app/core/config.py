from pydantic_settings import BaseSettings
from pydantic import EmailStr
from typing import Optional, List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Shakwa Multi-Tenant API"
    PROJECT_VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/shakwa_db"
    
    # JWT & Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 2880  # 48 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://shakwa-216307702725.europe-west1.run.app"
    ]

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-app-password"
    SMTP_FROM_NAME: str = "Shakwa"
    SMTP_FROM_EMAIL: str = "noreply@shakwa.com"
    
    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Speechmatics Configuration
    SPEECHMATICS_API_KEY: Optional[str] = None

    OLLAMA_API_KEY: Optional[str] = None

    # Redis Configuration (for SLA timers)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    SLA_DEFAULT_MINUTES: int = 3

    # How often the assignment retry worker polls for unassigned queued tickets (seconds)
    ASSIGNMENT_RETRY_INTERVAL_SECONDS: int = 60

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
# print("Loaded settings:", settings.dict())