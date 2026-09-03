from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)


def test_tts_synthesize_endpoint():
    """Verify POST /tts/synthesize securely calls Cartesia and returns WAV audio bytes."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFFmockwavdata"
        mock_post.return_value = mock_response

        response = client.post(
            "/tts/synthesize",
            json={"text": "Hello from AgentGuard!"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert response.content == b"RIFFmockwavdata"


def test_tts_synthesize_empty_text():
    """Verify validation error when text is empty."""
    response = client.post(
        "/tts/synthesize",
        json={"text": "   "},
    )
    assert response.status_code == 400
