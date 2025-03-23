from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Language Translator"
    
    # LibreTranslate Configuration
    LIBRE_TRANSLATE_URL: str = "http://localhost:5500"  # Changed port to 5500
    
    # Redis Configuration (for caching)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TTL: int = 3600  # Cache TTL in seconds

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_FAILURE_WINDOW: int = 60  # seconds
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 30  # seconds

    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS: int = 100  # requests per window
    RATE_LIMIT_WINDOW: int = 60  # window in seconds

    # File Storage Configuration
    STORAGE_PATH: str = "./storage/translations"  # Local path to store translations
    FILE_RETENTION_DAYS: int = 7  # Number of days to keep files
    
    # Storage settings
    STORAGE_TYPE: str = "local"  # Options: local, s3 (future)
    
    # AWS S3 settings (for future use)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    AWS_BUCKET_NAME: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 