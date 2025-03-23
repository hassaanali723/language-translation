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

class LibreTranslateService(BaseTranslationService):
    def __init__(self):
        self.base_url = settings.LIBRE_TRANSLATE_URL
        if not self.base_url:
            logger.error("LIBRE_TRANSLATE_URL is not set in configuration")
            raise ValueError("LIBRE_TRANSLATE_URL is not set in configuration")
            
        logger.info(f"Initializing LibreTranslate service with URL: {self.base_url}")
        
        try:
            self.cache = RedisCache()
            self.redis_available = True
        except:
            logger.warning("Redis not available, running without cache")
            self.redis_available = False
        self.failure_threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.failure_window = settings.CIRCUIT_BREAKER_FAILURE_WINDOW
        self.failures = []
        self.circuit_open = False
        self.reset_time = None
        
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
            self.failures.append(datetime.utcnow())
            if len(self.failures) >= self.failure_threshold:
                self.circuit_open = True
                self.reset_time = datetime.utcnow() + timedelta(seconds=settings.CIRCUIT_BREAKER_RESET_TIMEOUT)
            
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

    async def translate_file(self, file: UploadFile, source_lang: str, target_lang: str) -> tuple[str, str]:
        """
        Translate a file using LibreTranslate's file translation endpoint.
        Returns the URL to the translated file and the suggested filename.
        """
        try:
            # Check circuit breaker
            await self._check_circuit_breaker()
            
            logger.info("Translating file", extra={
                "file_name": file.filename,
                "source": source_lang,
                "target": target_lang,
                "content_type": file.content_type
            })
            
            # Read file content once to avoid multiple reads
            file_content = await file.read()
            
            # Log request details
            logger.info(f"Sending request to {self.base_url}/translate_file", extra={
                "url": f"{self.base_url}/translate_file",
                "file_size": len(file_content),
                "file_name": file.filename
            })
            
            try:
                # Try first with /translate_file endpoint
                async with httpx.AsyncClient(timeout=120.0) as client:
                    try:
                        # First attempt with /translate_file
                        response = await client.post(
                            f"{self.base_url}/translate_file",
                            files={'file': (file.filename, file_content, file.content_type)},
                            data={
                                'source': source_lang,
                                'target': target_lang
                            }
                        )
                        
                        # Log response status
                        logger.info(f"Received response with status {response.status_code}", extra={
                            "status_code": response.status_code
                        })
                        
                        response.raise_for_status()
                        
                        try:
                            response_data = response.json()
                            logger.info("Successfully parsed response JSON", extra={
                                "response_keys": list(response_data.keys())
                            })
                        except Exception as json_e:
                            # If not JSON, this might be direct file content response
                            logger.warning(f"Response is not JSON, might be direct file content", extra={
                                "content_type": response.headers.get("content-type"),
                                "content_length": len(response.content)
                            })
                            
                            # Generate a local URL for the file content
                            # Create temporary directory if it doesn't exist
                            os.makedirs("temp", exist_ok=True)
                            
                            # Generate translated filename
                            filename_parts = os.path.splitext(file.filename)
                            translated_filename = f"{filename_parts[0]}_{target_lang}{filename_parts[1]}"
                            
                            # Save translated file locally
                            file_path = os.path.join("temp", translated_filename)
                            with open(file_path, "wb") as f:
                                f.write(response.content)
                                
                            # Return a local URL
                            return f"/temp/{translated_filename}", translated_filename
                        
                        # Check the structure of the response
                        if 'translatedFileUrl' in response_data:
                            translated_file_url = response_data['translatedFileUrl']
                        else:
                            logger.warning("Response doesn't contain translatedFileUrl, checking for other patterns", extra={
                                "response_data": response_data
                            })
                            
                            # Check for other possible response formats
                            if 'url' in response_data:
                                translated_file_url = response_data['url']
                            elif 'translated_url' in response_data:
                                translated_file_url = response_data['translated_url']
                            else:
                                raise ValueError(f"Unrecognized response format. Got keys: {list(response_data.keys())}")
                        
                        # Generate translated filename
                        filename_parts = os.path.splitext(file.filename)
                        translated_filename = f"{filename_parts[0]}_{target_lang}{filename_parts[1]}"
                        
                        return translated_file_url, translated_filename
                        
                    except httpx.HTTPStatusError as status_e:
                        logger.warning(f"translate_file endpoint failed with status {status_e.response.status_code}, trying alternative approach", extra={
                            "error": str(status_e),
                            "status_code": status_e.response.status_code
                        })
                        raise
                        
            except httpx.TimeoutException as te:
                error_msg = f"Request to LibreTranslate timed out after 120 seconds: {str(te)}"
                logger.error(error_msg, extra={"file_name": file.filename})
                raise HTTPException(status_code=504, detail=error_msg)
                
        except httpx.HTTPError as e:
            self.failures.append(datetime.utcnow())
            if len(self.failures) >= self.failure_threshold:
                self.circuit_open = True
                self.reset_time = datetime.utcnow() + timedelta(seconds=settings.CIRCUIT_BREAKER_RESET_TIMEOUT)
            
            error_msg = f"File translation HTTP error: {str(e)}"
            
            # Add more diagnostics for connection error
            if isinstance(e, httpx.ConnectError):
                error_msg = f"Could not connect to LibreTranslate service at {self.base_url}: {str(e)}"
            
            logger.error(error_msg, extra={
                "error_type": type(e).__name__,
                "error_msg": str(e),
                "file_name": file.filename,
                "url": f"{self.base_url}/translate_file"
            })
            
            raise HTTPException(status_code=503, detail=error_msg)
            
        except Exception as e:
            error_msg = f"File translation general error: {str(e)}"
            logger.error(error_msg, extra={
                "error_type": type(e).__name__,
                "error_msg": str(e),
                "file_name": file.filename
            })
            raise HTTPException(status_code=500, detail=error_msg) 