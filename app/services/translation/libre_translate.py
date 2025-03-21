from typing import List, Dict
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.services.translation.base import BaseTranslationService
from app.schemas.translation import LanguageInfo
from app.services.cache.redis_cache import RedisCache
from fastapi import HTTPException
import asyncio
from datetime import datetime, timedelta

class LibreTranslateService(BaseTranslationService):
    def __init__(self):
        self.base_url = settings.LIBRE_TRANSLATE_URL
        try:
            self.cache = RedisCache()
            self.redis_available = True
        except:
            logger.warning_with_props("Redis not available, running without cache")
            self.redis_available = False
        self.failure_threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.failure_window = settings.CIRCUIT_BREAKER_FAILURE_WINDOW
        self.failures = []
        self.circuit_open = False
        self.reset_time = None
        
    async def _check_circuit_breaker(self):
        """Circuit breaker implementation"""
        if self.circuit_open:
            if datetime.utcnow() >= self.reset_time:
                self.circuit_open = False
                self.failures = []
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again later."
                )
                
        # Clean old failures
        self.failures = [f for f in self.failures 
                        if f > datetime.utcnow() - timedelta(seconds=self.failure_window)]
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # Check circuit breaker
            await self._check_circuit_breaker()
            
            # Check cache if Redis is available
            if self.redis_available:
                cached = await self.cache.get_translation(text, source_lang, target_lang)
                if cached:
                    logger.info_with_props("Translation found in cache", 
                            props={"text_length": len(text), "source": source_lang, "target": target_lang})
                    return cached
            
            logger.info_with_props("Performing translation", 
                       props={"text_length": len(text), "source": source_lang, "target": target_lang})
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/translate",
                    json={
                        "q": text,
                        "source": source_lang,
                        "target": target_lang
                    }
                )
                response.raise_for_status()
                translated = response.json()["translatedText"]
                
                # Cache the result if Redis is available
                if self.redis_available:
                    await self.cache.set_translation(text, source_lang, target_lang, translated)
                return translated
                
        except httpx.HTTPError as e:
            self.failures.append(datetime.utcnow())
            if len(self.failures) >= self.failure_threshold:
                self.circuit_open = True
                self.reset_time = datetime.utcnow() + timedelta(seconds=settings.CIRCUIT_BREAKER_RESET_TIMEOUT)
            
            logger.error_with_props("Translation failed", 
                        props={"error": str(e), "text_length": len(text)})
            raise HTTPException(status_code=500, detail="Translation service unavailable")
    
    async def get_supported_languages(self) -> List[LanguageInfo]:
        try:
            # Check cache if Redis is available
            if self.redis_available:
                cached = await self.cache.get_languages()
                if cached:
                    return [LanguageInfo(**lang) for lang in cached]
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/languages")
                response.raise_for_status()
                languages = response.json()
                
                # Transform and cache if Redis is available
                language_info = [
                    LanguageInfo(code=lang["code"], name=lang["name"])
                    for lang in languages
                ]
                if self.redis_available:
                    await self.cache.set_languages([lang.dict() for lang in language_info])
                return language_info
                
        except httpx.HTTPError as e:
            logger.error_with_props("Failed to fetch languages", props={"error": str(e)})
            raise HTTPException(status_code=500, detail="Failed to fetch supported languages")
    
    async def detect_language(self, text: str) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/detect",
                    json={"q": text}
                )
                response.raise_for_status()
                detections = response.json()
                return sorted(detections, key=lambda x: x["confidence"], reverse=True)[0]["language"]
                
        except httpx.HTTPError as e:
            logger.error_with_props("Language detection failed", 
                        props={"error": str(e), "text_length": len(text)})
            raise HTTPException(status_code=500, detail="Language detection failed") 