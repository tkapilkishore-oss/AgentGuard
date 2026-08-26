from decimal import Decimal

# pyrefly: ignore [missing-import]
import pytest

# pyrefly: ignore [missing-import]
from fastapi import HTTPException

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

# pyrefly: ignore [missing-import]
from pydantic import ValidationError

from backend.app.api.schemas import AgentClaim, ApiResponse, ProposeRequest
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_app_instantiation():
    """Verify FastAPI app is instantiated cleanly with correct title."""
    assert app.title == "Agentic Commerce Firewall API"


def test_api_response_envelope_constructors():
    """Verify ApiResponse helper constructors and canonical envelope shapes."""
    ok_resp = ApiResponse.ok({"key": "value"})
    assert ok_resp.success is True
    assert ok_resp.data == {"key": "value"}
    assert ok_resp.error is None

    fail_resp = ApiResponse.fail("PRICE_MISMATCH", "Price claimed does not match catalog")
    assert fail_resp.success is False
    assert fail_resp.data is None
    assert fail_resp.error is not None
    assert fail_resp.error.code == "PRICE_MISMATCH"
    assert fail_resp.error.message == "Price claimed does not match catalog"


def test_health_endpoint(client: TestClient):
    """Verify GET /health returns 200 OK with standard success envelope."""
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"] == {"status": "ok", "service": "Agentic Commerce Firewall"}
    assert json_data["error"] is None


def test_agent_claim_strips_extra_fields():
    """Verify injected merchant_id and total fields are ignored/stripped by schema construction."""
    raw_payload = {
        "user_id": "u-001",
        "mandate_id": "m-001",
        "total": 9999.00,  # Top-level injected total
        "agent_claim": {
            "product_id": "prod-001",
            "claimed_price": 1999.00,
            "quantity": 2,
            "merchant_id": "merchant-hacked",  # Injected merchant
            "total": 3998.00,  # Injected claim total
        },
    }
    req = ProposeRequest.model_validate(raw_payload)
    assert req.user_id == "u-001"
    assert req.mandate_id == "m-001"
    assert req.agent_claim.product_id == "prod-001"
    assert req.agent_claim.claimed_price == Decimal("1999.00")
    assert req.agent_claim.quantity == 2

    # Confirm injected merchant_id and total fields do NOT exist on parsed objects
    assert not hasattr(req, "total")
    assert not hasattr(req.agent_claim, "merchant_id")
    assert not hasattr(req.agent_claim, "total")


@pytest.mark.parametrize(
    "quantity, is_valid",
    [
        (1, True),
        (10, True),
        (0, False),
        (-1, False),
        (11, False),
        (True, False),
        (False, False),
        (1.5, False),
    ],
)
def test_quantity_validation_boundaries(quantity, is_valid):
    """Verify integer quantity bounds (1 <= q <= 10) and strict non-boolean, non-float typing."""
    raw_claim = {"product_id": "prod-001", "claimed_price": 100.00, "quantity": quantity}
    if is_valid:
        claim = AgentClaim.model_validate(raw_claim)
        assert claim.quantity == quantity
    else:
        with pytest.raises(ValidationError):
            AgentClaim.model_validate(raw_claim)


@pytest.mark.parametrize(
    "price, is_valid",
    [
        ("1999.00", True),
        ("0.01", True),
        ("0.00", False),
        ("-10.00", False),
        ("invalid-price", False),
    ],
)
def test_monetary_validation_boundaries(price, is_valid):
    """Verify claimed_price must be a positive decimal."""
    raw_claim = {"product_id": "prod-001", "claimed_price": price, "quantity": 1}
    if is_valid:
        claim = AgentClaim.model_validate(raw_claim)
        assert claim.claimed_price == Decimal(price)
    else:
        with pytest.raises(ValidationError):
            AgentClaim.model_validate(raw_claim)


def test_validation_error_formatting():
    """Verify malformed requests return 400 Bad Request with MALFORMED_REQUEST error envelope."""
    @app.post("/test-validation-endpoint")
    def _endpoint(payload: ProposeRequest):
        return ApiResponse.ok({"user_id": payload.user_id})

    test_client = TestClient(app)
    response = test_client.post("/test-validation-endpoint", json={"user_id": "u1"})
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "MALFORMED_REQUEST"
    assert "Invalid request payload" in json_data["error"]["message"]


def test_custom_http_exception_formatting():
    """Verify HTTPExceptions return exact status code and standard failure envelope."""
    @app.get("/test-http-exc-endpoint")
    def _endpoint():
        raise HTTPException(status_code=403, detail="MANDATE_EXPIRED")

    test_client = TestClient(app)
    response = test_client.get("/test-http-exc-endpoint")
    assert response.status_code == 403
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "MANDATE_EXPIRED"


def test_unhandled_exception_formatting():
    """Verify unhandled exceptions return 500 Internal Server Error with sanitized failure envelope."""
    @app.get("/test-unhandled-exc-endpoint")
    def _endpoint():
        raise RuntimeError("Sensitive DB path /var/lib/postgresql/secrets")

    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.get("/test-unhandled-exc-endpoint")
    assert response.status_code == 500
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["data"] is None
    assert json_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Ensure no internal error detail or filesystem path is leaked
    assert "postgresql" not in json_data["error"]["message"]
    assert json_data["error"]["message"] == "An unexpected server error occurred."
