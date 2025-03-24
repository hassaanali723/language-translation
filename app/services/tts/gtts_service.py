from pathlib import Path
import uuid
from gtts import gTTS
from app.core.config import settings
from app.core.logging import logger
from app.services.tts.base import TTSService

class GTTSService(TTSService):
    """Google Translate TTS service implementation"""
    
    def __init__(self):
        self.audio_path = Path(settings.AUDIO_STORAGE_PATH)
        self.audio_path.mkdir(parents=True, exist_ok=True)
    
    async def convert_text_to_speech(self, text: str, language: str, speed: float = None, 
                                   pitch: int = None, volume: int = None) -> tuple[str, str]:
        """
        Convert text to speech using Google Translate's TTS engine.
        
        Args:
            text: The text to convert to speech
            language: The language code (e.g., 'en', 'es', 'fr')
            speed: Speech rate multiplier (optional)
            pitch: Voice pitch (optional, not supported by gTTS)
            volume: Volume level (optional, not supported by gTTS)
            
        Returns:
            Tuple of (file_name, file_url)
        """
        try:
            # Generate unique file ID and path
            file_id = str(uuid.uuid4())
            file_path = self.audio_path / f"{file_id}.mp3"
            
            # Create gTTS object and save to file
            # Note: gTTS only supports 'slow' parameter for speed
            is_slow = bool(speed and speed < 1.0)
            tts = gTTS(text=text, lang=language, slow=is_slow)
            tts.save(str(file_path))
            
            # Generate audio file URL
            audio_url = f"/api/v1/tts/audio/{file_id}"
            
            return file_path.name, audio_url
            
        except Exception as e:
            logger.error(f"GTTSService error: {str(e)}")
            raise 