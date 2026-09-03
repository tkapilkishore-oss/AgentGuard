import logging
import httpx
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])

CARTESIA_VOICE_ID_SKYLAR = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
CARTESIA_MODEL_ID = "sonic-3"
CARTESIA_API_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = "2024-06-10"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Cleaned text to synthesize")


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest) -> Response:
    """
    Synthesize human-like speech using Cartesia TTS (Skylar - Friendly Guide).
    Returns WAV audio bytes directly to the frontend.
    """
    api_key = settings.CARTESIA_API_KEY
    if not api_key:
        logger.error("Cartesia API key is not configured in backend environment.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CARTESIA_KEY_MISSING",
                "message": "Cartesia API key is not configured on the server.",
            },
        )

    cleaned_text = request.text.strip()
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_TEXT",
                "message": "Text for speech synthesis cannot be empty.",
            },
        )

    headers = {
        "X-API-Key": api_key,
        "Cartesia-Version": CARTESIA_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "model_id": CARTESIA_MODEL_ID,
        "transcript": cleaned_text,
        "voice": {
            "mode": "id",
            "id": CARTESIA_VOICE_ID_SKYLAR,
            "__experimental_controls": {
                "speed": -0.3,
            },
        },
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
        "language": "en",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(CARTESIA_API_URL, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(
                "Cartesia TTS API error. HTTP %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "CARTESIA_TTS_ERROR",
                    "message": f"Cartesia TTS failed with status {resp.status_code}.",
                },
            )

        return Response(
            content=resp.content,
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline; filename=speech.wav",
            },
        )

    except httpx.RequestError as exc:
        logger.error("Network error communicating with Cartesia: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "CARTESIA_NETWORK_ERROR",
                "message": "Failed to connect to Cartesia TTS service.",
            },
        )
