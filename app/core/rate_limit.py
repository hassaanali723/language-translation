from fastapi import HTTPException
from redis import Redis
from app.core.config import settings
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.rate_limit = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW

    async def check_rate_limit(self, client_id: str):
        """Check if client has exceeded rate limit"""
        current = datetime.utcnow()
        key = f"rate_limit:{client_id}:{current.minute}"
        
        # Get current count
        count = self.redis.get(key)
        if count is None:
            # First request in this window
            self.redis.setex(key, self.window, 1)
            return True
            
        count = int(count)
        if count >= self.rate_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
            
        # Increment counter
        self.redis.incr(key)
        return True 