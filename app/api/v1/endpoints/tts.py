from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
from app.schemas.tts import TTSRequest, TTSResponse
from app.services.tts.gtts_service import GTTSService

router = APIRouter()
tts_service = GTTSService()

@router.post("/convert", response_model=TTSResponse)
async def convert_text_to_speech(request: TTSRequest) -> TTSResponse:
    """
    Convert text to speech using Google Translate's TTS engine.
    Returns a URL to download the generated audio file.
    """
    try:
        file_name, file_url = await tts_service.convert_text_to_speech(
            text=request.text,
            language=request.language,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume
        )
        
        return TTSResponse(
            success=True,
            audio_file_name=file_name,
            audio_file_url=file_url,
            language=request.language
        )
        
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating speech: {str(e)}"
        )

@router.get("/audio/{file_id}")
async def get_audio_file(file_id: str):
    """Stream the audio file."""
    try:
        audio_path = Path(settings.AUDIO_STORAGE_PATH)
        file_path = audio_path / f"{file_id}.mp3"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        def iterfile():
            with open(file_path, 'rb') as f:
                yield from f
        
        return StreamingResponse(
            iterfile(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="{file_path.name}"'
            }
        )
    except Exception as e:
        logger.error(f"Error streaming audio file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error streaming audio file") 