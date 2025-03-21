from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    SupportedLanguagesResponse,
    LanguageInfo
)
from app.services.translation.libre_translate import LibreTranslateService
from app.services.translation.base import BaseTranslationService

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