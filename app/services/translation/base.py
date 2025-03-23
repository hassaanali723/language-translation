from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from app.schemas.translation import LanguageInfo
from fastapi import UploadFile

class BaseTranslationService(ABC):
    """Abstract base class for translation services"""
    
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source language to target language
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[LanguageInfo]:
        """
        Get list of supported languages
        
        Returns:
            List of supported languages with their codes and names
        """
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text
        
        Args:
            text: Text to detect language for
            
        Returns:
            Detected language code
        """
        pass
        
    @abstractmethod
    async def translate_file(self, file: UploadFile, source_lang: str, target_lang: str) -> Tuple[str, str]:
        """
        Translate a document file from source language to target language
        
        Args:
            file: File to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Tuple containing (translated_file_url, translated_filename)
        """
        pass 