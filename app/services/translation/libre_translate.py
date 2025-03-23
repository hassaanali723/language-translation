from typing import List, Dict
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.services.translation.base import BaseTranslationService
from app.schemas.translation import LanguageInfo
from app.services.cache.redis_cache import RedisCache
from fastapi import HTTPException, UploadFile
import asyncio
from datetime import datetime, timedelta
import os
import uuid
from pathlib import Path

class CircuitBreaker:
    def __init__(self, failure_threshold: int, failure_window: int, reset_timeout: int):
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.reset_timeout = reset_timeout
        self.failures = []
        self.is_open = False
        self.reset_time = None

    def record_failure(self):
        current_time = datetime.utcnow()
        self.failures = [f for f in self.failures 
                        if f > current_time - timedelta(seconds=self.failure_window)]
        self.failures.append(current_time)
        
        if len(self.failures) >= self.failure_threshold:
            self.is_open = True
            self.reset_time = current_time + timedelta(seconds=self.reset_timeout)

    def allow_request(self) -> bool:
        if not self.is_open:
            return True
            
        if datetime.utcnow() >= self.reset_time:
            self.is_open = False
            self.failures = []
            return True
            
        return False

class LibreTranslateService(BaseTranslationService):
    def __init__(self):
        self.base_url = settings.LIBRE_TRANSLATE_URL
        if not self.base_url:
            logger.error("LIBRE_TRANSLATE_URL is not set in configuration")
            raise ValueError("LIBRE_TRANSLATE_URL is not set in configuration")
            
        logger.info(f"Initializing LibreTranslate service with URL: {self.base_url}")
        
        # Create storage directory if it doesn't exist
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        try:
            self.cache = RedisCache()
            self.redis_available = True
        except:
            logger.warning("Redis not available, running without cache")
            self.redis_available = False
            
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            failure_window=settings.CIRCUIT_BREAKER_FAILURE_WINDOW,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_TIMEOUT
        )
        self.headers = {}

    def _is_text_file(self, filename: str) -> bool:
        """Check if the file is a text file based on extension."""
        text_extensions = {'.txt', '.json', '.csv', '.md', '.log'}
        return os.path.splitext(filename)[1].lower() in text_extensions

    async def health_check(self) -> bool:
        """Check if LibreTranslate service is available and responsive."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/languages")
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"LibreTranslate health check failed: {str(e)}", extra={
                "error_type": type(e).__name__,
                "url": self.base_url
            })
            return False
        
    async def _check_circuit_breaker(self):
        """Circuit breaker implementation"""
        if self.circuit_breaker.is_open:
            if datetime.utcnow() >= self.circuit_breaker.reset_time:
                self.circuit_breaker.is_open = False
                self.circuit_breaker.failures = []
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable. Please try again later."
                )
                
        # Clean old failures
        self.circuit_breaker.failures = [f for f in self.circuit_breaker.failures 
                        if f > datetime.utcnow() - timedelta(seconds=self.circuit_breaker.failure_window)]
    
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # Check circuit breaker
            await self._check_circuit_breaker()
            
            # Check cache if Redis is available
            if self.redis_available:
                cached = await self.cache.get_translation(text, source_lang, target_lang)
                if cached:
                    logger.info("Translation found in cache", extra={
                        "text_len": len(text), 
                        "source": source_lang, 
                        "target": target_lang
                    })
                    return cached
            
            logger.info("Performing translation", extra={
                "text_len": len(text), 
                "source": source_lang, 
                "target": target_lang
            })
            
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
            self.circuit_breaker.record_failure()
            logger.error("Translation failed", extra={
                "error_msg": str(e), 
                "text_len": len(text)
            })
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
            logger.error("Failed to fetch languages", extra={"error_msg": str(e)})
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
            logger.error("Language detection failed", extra={
                "error_msg": str(e), 
                "text_len": len(text)
            })
            raise HTTPException(status_code=500, detail="Language detection failed")

    def _save_file_locally(self, content: bytes, original_filename: str) -> tuple[str, str]:
        """Save file to local storage and return file ID and path."""
        # Generate unique ID and filename
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(original_filename)[1]
        filename = f"{file_id}{extension}"
        
        # Save file
        file_path = self.storage_path / filename
        with open(file_path, 'wb') as f:
            f.write(content)
            
        # Save metadata (creation time, original filename)
        meta_path = self.storage_path / f"{file_id}.meta"
        with open(meta_path, 'w') as f:
            f.write(f"{original_filename}\n{datetime.utcnow().isoformat()}")
            
        return file_id, str(file_path)

    def _get_translated_filename(self, original_filename: str, target_lang: str) -> str:
        """Generate a filename for the translated file."""
        name, ext = os.path.splitext(original_filename)
        return f"{name}_{target_lang}{ext}"

    async def translate_file(self, file: UploadFile, source_lang: str, target_lang: str) -> dict:
        """Translate a file using LibreTranslate."""
        try:
            logger.info(f"Starting file translation", extra={
                "file_name": file.filename,
                "file_content_type": file.content_type,
                "source_lang": source_lang,
                "target_lang": target_lang
            })
            
            file_content = await file.read()
            logger.info(f"File read successfully", extra={
                "file_size": len(file_content),
                "file_name": file.filename
            })
            
            files = {"file": (file.filename, file_content)}
            data = {"source": source_lang, "target": target_lang}
            
            logger.info(f"Sending request to LibreTranslate", extra={
                "url": f"{self.base_url}/translate_file",
                "file_name": file.filename
            })
            
            # Increased timeout to 120 seconds for file translation
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    response = await client.post(
                        f"{self.base_url}/translate_file",
                        files=files,
                        data=data,
                        headers=self.headers
                    )
                    
                    logger.info(f"Received response from LibreTranslate", extra={
                        "status_code": response.status_code,
                        "response_length": len(response.content),
                        "file_name": file.filename
                    })
                    
                    if response.status_code != 200:
                        error_detail = response.text
                        try:
                            error_json = response.json()
                            if 'error' in error_json:
                                error_detail = error_json['error']
                        except Exception as json_e:
                            logger.error(f"Failed to parse error response as JSON", extra={
                                "error": str(json_e),
                                "response_text": response.text[:500]  # Log first 500 chars of response
                            })
                            
                        logger.error(f"LibreTranslate API error", extra={
                            "status_code": response.status_code,
                            "error_detail": error_detail,
                            "file_name": file.filename,
                            "headers": dict(response.headers),
                            "url": str(response.url)
                        })
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Translation failed: {error_detail}"
                        )
                    
                    response_data = response.json()
                    if "translatedFileUrl" not in response_data:
                        logger.error("Missing translatedFileUrl in response", extra={
                            "response_data": response_data,
                            "file_name": file.filename
                        })
                        raise HTTPException(
                            status_code=500,
                            detail="Invalid response from translation service: missing translated file URL"
                        )
                    
                    # Get translated file from LibreTranslate
                    translated_url = response_data["translatedFileUrl"]
                    logger.info(f"Downloading translated file", extra={
                        "translated_url": translated_url,
                        "file_name": file.filename
                    })
                    
                    # Also use increased timeout for downloading the translated file
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        translated_response = await client.get(translated_url)
                        if translated_response.status_code != 200:
                            logger.error(f"Failed to download translated file", extra={
                                "status_code": translated_response.status_code,
                                "url": translated_url,
                                "response": translated_response.text[:500]
                            })
                            raise HTTPException(
                                status_code=translated_response.status_code,
                                detail=f"Failed to download translated file: {translated_response.text}"
                            )
                        
                        # Save translated file locally
                        translated_filename = self._get_translated_filename(file.filename, target_lang)
                        file_id, file_path = self._save_file_locally(
                            translated_response.content,
                            translated_filename
                        )
                        
                        logger.info(f"Translation completed successfully", extra={
                            "original_file": file.filename,
                            "translated_file": translated_filename,
                            "file_id": file_id
                        })
                        
                        return {
                            "success": True,
                            "translated_file_name": translated_filename,
                            "translated_file_url": f"/api/v1/translation/download/{file_id}",
                            "source_lang": source_lang,
                            "target_lang": target_lang
                        }
                        
                except httpx.TimeoutException as e:
                    logger.error(f"Request timeout", extra={
                        "timeout_seconds": 120.0,  # Updated timeout in error message
                        "error": str(e),
                        "file_name": file.filename
                    })
                    raise HTTPException(
                        status_code=504,
                        detail="Translation request timed out after 120 seconds. Please try with a smaller file or try again later."
                    )
                except httpx.RequestError as e:
                    logger.error(f"Request failed", extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "file_name": file.filename
                    })
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to connect to translation service: {str(e)}"
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during file translation", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "file_name": file.filename,
                "traceback": str(e.__traceback__)
            })
            raise HTTPException(
                status_code=500,
                detail=f"File translation failed: {str(e)}"
            )

