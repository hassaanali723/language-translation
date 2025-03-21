from pydantic import BaseModel, Field
from typing import Optional, List

class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    source_lang: str = Field(..., description="Source language code (e.g., 'en', 'es', 'fr')")
    target_lang: str = Field(..., description="Target language code (e.g., 'en', 'es', 'fr')")

class TranslationResponse(BaseModel):
    translated_text: str = Field(..., description="Translated text")
    source_lang: str = Field(..., description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    original_text: str = Field(..., description="Original text")

class LanguageInfo(BaseModel):
    code: str = Field(..., description="Language code (e.g., 'en')")
    name: str = Field(..., description="Language name (e.g., 'English')")

class SupportedLanguagesResponse(BaseModel):
    languages: List[LanguageInfo] = Field(..., description="List of supported languages") 