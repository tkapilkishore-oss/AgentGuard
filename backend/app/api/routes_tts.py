import logging
import re
import httpx
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])

DEEPGRAM_TTS_URL = "https://api.deepgram.com/v2/speak"
DEEPGRAM_TTS_MODEL = "flux-brooke-en"

_tts_client: httpx.AsyncClient | None = None


def normalize_spoken_text(text: str) -> str:
    """
    Normalizes technical terms and machine-readable decision codes for natural TTS pronunciation.
    Spells underscores naturally (e.g. PRICE_MISMATCH -> price mismatch) and formats SHA-256
    deliberately as 'S H A, two five six'.
    """
    if not text:
        return text

    normalized = text
    # Machine-readable security decision codes
    normalized = re.sub(r"\bPRICE_MISMATCH\b", "price mismatch", normalized)
    normalized = re.sub(r"\bMANDATE_REVOKED\b", "mandate revoked", normalized)
    normalized = re.sub(r"\bREPLAY_DETECTED\b", "replay detected", normalized)
    normalized = re.sub(r"\bBUDGET_EXCEEDED\b", "budget exceeded", normalized)
    normalized = re.sub(r"\bPOLICY_VIOLATION\b", "policy violation", normalized)
    normalized = re.sub(r"\bRATE_LIMITED\b", "rate limited", normalized)
    normalized = re.sub(r"\bUNAUTHORIZED_AGENT\b", "unauthorized agent", normalized)
    normalized = re.sub(r"\bEXPIRED_MANDATE\b", "expired mandate", normalized)
    normalized = re.sub(r"\bITEM_RESTRICTED\b", "item restricted", normalized)
    normalized = re.sub(r"\bMERCHANT_RESTRICTED\b", "merchant restricted", normalized)

    # Deliberately spell SHA-256 character-by-character
    normalized = re.sub(r"\bSHA[- ]?256\b", "S H A, two five six", normalized, flags=re.IGNORECASE)

    return normalized


def get_tts_client() -> httpx.AsyncClient:
    global _tts_client
    if _tts_client is None or _tts_client.is_closed:
        _tts_client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0),
        )
    return _tts_client


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Cleaned text to synthesize")


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest) -> Response:
    """
    Synthesize human-like speech using Deepgram TTS (Brooke - flux-brooke-en).
    Returns audio/mpeg bytes directly to the frontend.
    """
    api_key = settings.DEEPGRAM_API_KEY
    if not api_key:
        logger.error("Deepgram API key is not configured in backend environment.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEEPGRAM_KEY_MISSING",
                "message": "Deepgram API key is not configured on the server.",
            },
        )

    cleaned_text = normalize_spoken_text(request.text.strip())
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_TEXT",
                "message": "Text for speech synthesis cannot be empty.",
            },
        )

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "text": cleaned_text,
    }

    params = {
        "model": DEEPGRAM_TTS_MODEL,
    }

    try:
        client = get_tts_client()
        resp = await client.post(DEEPGRAM_TTS_URL, params=params, json=payload, headers=headers)

        if resp.status_code != 200:
            logger.error(
                "Deepgram TTS API error. HTTP %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "DEEPGRAM_TTS_ERROR",
                    "message": f"Deepgram TTS failed with status {resp.status_code}.",
                },
            )

        return Response(
            content=resp.content,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline; filename=speech.mp3",
            },
        )

    except httpx.RequestError as exc:
        logger.error("Network error communicating with Deepgram: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "DEEPGRAM_NETWORK_ERROR",
                "message": "Failed to connect to Deepgram TTS service.",
            },
        )
