"""
Core configuration settings for FinSentiq.
Loaded from environment variables with fallback defaults.
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "FinSentiq"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production-finsentiq-2026", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://finsentiq.vercel.app",
        "https://finsentiq.onrender.com"
    ]
    
    # LLM / Groq
    GROQ_API_KEY: str = Field(default="", env="GROQ_API_KEY")
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    
    # Feed & Cache Sync
    FEED_FETCH_INTERVAL_MINUTES: int = 10
    CACHE_TTL_SECONDS: int = 600
    
    # Persistence
    DATA_DIR: str = "data"
    COMPANY_CSV_PATH: str = "app/company.csv"
    
    # Redis (Optional in dev, required in high-scale multi-worker cloud)
    REDIS_URL: str = Field(default="", env="REDIS_URL")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
