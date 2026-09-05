from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import httpx
from backend.app.main import app

client = TestClient(app)


def test_tts_synthesize_endpoint():
    """Verify POST /tts/synthesize securely calls Deepgram and returns MP3 audio bytes."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", "mock-test-key"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"\xff\xfb\x90\x44mockmp3data"
            mock_post.return_value = mock_response

            response = client.post(
                "/tts/synthesize",
                json={"text": "Hello from AgentGuard!"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"
            assert response.content == b"\xff\xfb\x90\x44mockmp3data"
            mock_post.assert_called_once()
            assert mock_post.call_args.kwargs.get("params", {}).get("model") == "flux-brooke-en"


def test_tts_synthesize_missing_key():
    """Verify HTTP 500 when Deepgram API key is missing."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", ""):
        response = client.post(
            "/tts/synthesize",
            json={"text": "Hello without key"},
        )
        assert response.status_code == 500
        error = response.json().get("error") or response.json().get("detail") or {}
        assert error.get("code") == "DEEPGRAM_KEY_MISSING"


def test_tts_synthesize_deepgram_error():
    """Verify HTTP 502 when Deepgram returns an upstream error."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", "mock-test-key"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = '{"err_code": "INVALID_REQUEST"}'
            mock_post.return_value = mock_response

            response = client.post(
                "/tts/synthesize",
                json={"text": "Hello Deepgram error"},
            )
            assert response.status_code == 502
            error = response.json().get("error") or response.json().get("detail") or {}
            assert error.get("code") == "DEEPGRAM_TTS_ERROR"


def test_tts_synthesize_network_error():
    """Verify HTTP 502 when a network error occurs connecting to Deepgram."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", "mock-test-key"):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            response = client.post(
                "/tts/synthesize",
                json={"text": "Hello network error"},
            )
            assert response.status_code == 502
            error = response.json().get("error") or response.json().get("detail") or {}
            assert error.get("code") == "DEEPGRAM_NETWORK_ERROR"


def test_tts_synthesize_empty_text():
    """Verify validation error when text is empty."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", "mock-test-key"):
        response = client.post(
            "/tts/synthesize",
            json={"text": "   "},
        )
        assert response.status_code == 400
        error = response.json().get("error") or response.json().get("detail") or {}
        assert error.get("code") == "EMPTY_TEXT"


def test_tts_synthesize_security_terms_normalization():
    """Verify PRICE_MISMATCH becomes 'price mismatch' and SHA-256 becomes 'S H A, two five six'."""
    with patch("backend.app.api.routes_tts.settings.DEEPGRAM_API_KEY", "mock-test-key"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"\xff\xfb\x90\x44mockmp3data"
            mock_post.return_value = mock_response

            response = client.post(
                "/tts/synthesize",
                json={
                    "text": "The transaction failed with PRICE_MISMATCH and was hashed with SHA-256 into the audit ledger."
                },
            )

            assert response.status_code == 200
            # Inspect payload sent to Deepgram
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs.get("json", {})
            sent_text = payload.get("text", "")
            assert "price mismatch" in sent_text
            assert "PRICE_MISMATCH" not in sent_text
            assert "S H A, two five six" in sent_text
            assert "SHA-256" not in sent_text


