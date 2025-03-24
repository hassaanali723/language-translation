from abc import ABC, abstractmethod
from typing import Optional

class TTSService(ABC):
    """Base class for TTS services"""
    
    @abstractmethod
    async def convert_text_to_speech(self, text: str, language: str, speed: float = None, 
                                   pitch: int = None, volume: int = None) -> tuple[str, str]:
        """
        Convert text to speech.
        
        Args:
            text: The text to convert to speech
            language: The language code
            speed: Speech rate multiplier (optional)
            pitch: Voice pitch (optional)
            volume: Volume level (optional)
            
        Returns:
            Tuple of (file_name, file_url)
        """
        pass

class BaseTTSService(ABC):
    """Base class for Text-to-Speech services."""
    
    @abstractmethod
    async def text_to_speech(
        self,
        text: str,
        language: str,
        speed: Optional[int] = None,
        pitch: Optional[int] = None,
        volume: Optional[int] = None
    ) -> dict:
        """
        Convert text to speech.
        
        Args:
            text: The text to convert to speech
            language: Language code (e.g., 'en', 'es', 'fr')
            speed: Speech rate (implementation specific)
            pitch: Voice pitch (implementation specific)
            volume: Volume level (implementation specific)
            
        Returns:
            dict: Contains audio file information including:
                - success: bool
                - audio_file_name: str
                - audio_file_url: str
                - language: str
        """
        pass 