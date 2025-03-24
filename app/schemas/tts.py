from pydantic import BaseModel, Field
from typing import Optional

class TTSRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech")
    language: str = Field(..., description="Language code (e.g., 'en', 'es', 'fr', etc.)")
    speed: Optional[float] = Field(
        None,
        description="Speech rate multiplier (implementation specific)",
    )
    pitch: Optional[int] = Field(
        None,
        description="Voice pitch (implementation specific)",
    )
    volume: Optional[int] = Field(
        None,
        description="Volume level (implementation specific)",
    )

class TTSResponse(BaseModel):
    success: bool
    audio_file_name: str
    audio_file_url: str
    language: str 