from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List
import os
from pathlib import Path
from datetime import datetime, timezone

from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    SupportedLanguagesResponse,
    LanguageInfo,
    FileTranslationResponse
)
from app.services.translation.libre_translate import LibreTranslateService
from app.services.translation.base import BaseTranslationService
from app.core.logging import logger
from app.core.config import settings

router = APIRouter()

async def get_translation_service() -> BaseTranslationService:
    return LibreTranslateService()

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    translation_service: BaseTranslationService = Depends(get_translation_service)
):
    try:
        translated_text = await translation_service.translate(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        return TranslationResponse(
            translated_text=translated_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            original_text=request.text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages", response_model=SupportedLanguagesResponse)
async def get_supported_languages(
    translation_service: BaseTranslationService = Depends(get_translation_service)
):
    try:
        languages = await translation_service.get_supported_languages()
        return SupportedLanguagesResponse(languages=languages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect", response_model=str)
async def detect_language(
    text: str,
    translation_service: BaseTranslationService = Depends(get_translation_service)
):
    try:
        detected_lang = await translation_service.detect_language(text)
        return detected_lang
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate/file", response_model=FileTranslationResponse)
async def translate_file(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    translation_service: BaseTranslationService = Depends(get_translation_service)
):
    """
    Translate a document file from source language to target language.
    Supports formats that LibreTranslate can handle (e.g., .txt, .docx, .pdf)
    """
    try:
        # Check if service is available
        if hasattr(translation_service, 'health_check'):
            is_healthy = await translation_service.health_check()
            if not is_healthy:
                raise HTTPException(
                    status_code=503, 
                    detail="Translation service is currently unavailable. Please try again later."
                )
        
        # Validate file size (optional, adjust limit as needed)
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=400, detail="File too large")
        
        logger.info(f"Processing file translation request", extra={
            "file_name": file.filename,
            "file_size": file_size,
            "source_lang": source_lang,
            "target_lang": target_lang
        })
        
        # Reset file position after reading
        await file.seek(0)
        
        # Translate file
        result = await translation_service.translate_file(
            file,
            source_lang,
            target_lang
        )
        
        return FileTranslationResponse(
            success=result["success"],
            translated_file_name=result["translated_file_name"],
            source_lang=result["source_lang"],
            target_lang=result["target_lang"],
            translated_file_url=result["translated_file_url"]
        )
        
    except HTTPException as e:
        # Pass through HTTP exceptions from the service
        logger.error(f"File translation HTTP exception: {e.detail}", extra={
            "file_name": file.filename,
            "status_code": e.status_code
        })
        raise
    except Exception as e:
        error_message = str(e)
        logger.error(f"File translation failed: {error_message}", extra={
            "file_name": file.filename
        })
        raise HTTPException(status_code=500, detail=error_message)

@router.get("/health", status_code=200)
async def check_health(
    translation_service: BaseTranslationService = Depends(get_translation_service)
):
    """
    Check if the translation service is up and running
    """
    try:
        # Check if service has a health check method
        if hasattr(translation_service, 'health_check'):
            is_healthy = await translation_service.health_check()
            if not is_healthy:
                return {"status": "error", "message": "Translation service is not available"}
            return {"status": "ok", "message": "Translation service is available"}
        else:
            # Fallback to getting languages as a health check
            await translation_service.get_supported_languages()
            return {"status": "ok", "message": "Translation service is available"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 503 

@router.get("/download/{file_id}")
async def download_translated_file(file_id: str):
    """Download a translated file by its ID."""
    try:
        # Find the file with any extension
        storage_path = Path(settings.STORAGE_PATH)
        files = list(storage_path.glob(f"{file_id}.*"))
        file_path = next((f for f in files if not f.name.endswith('.meta')), None)
        
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")
            
        # Get original filename from metadata
        meta_path = storage_path / f"{file_id}.meta"
        original_filename = file_path.name
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                original_filename = f.readline().strip()
        
        # Stream the file
        def iterfile():
            with open(file_path, 'rb') as f:
                yield from f
                
        return StreamingResponse(
            iterfile(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{original_filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error downloading file") 