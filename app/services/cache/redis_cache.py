from typing import Optional
import json
from redis import Redis
from app.core.config import settings

class RedisCache:
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.ttl = settings.REDIS_TTL

    def _generate_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate a unique key for the translation"""
        return f"trans:{source_lang}:{target_lang}:{hash(text)}"

    async def get_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation if exists"""
        key = self._generate_key(text, source_lang, target_lang)
        return self.redis.get(key)

    async def set_translation(self, text: str, source_lang: str, target_lang: str, translated_text: str):
        """Cache a translation"""
        key = self._generate_key(text, source_lang, target_lang)
        self.redis.setex(key, self.ttl, translated_text)

    async def get_languages(self) -> Optional[list]:
        """Get cached languages list"""
        return json.loads(self.redis.get("languages")) if self.redis.get("languages") else None

    async def set_languages(self, languages: list):
        """Cache languages list"""
        self.redis.setex("languages", self.ttl, json.dumps(languages)) 