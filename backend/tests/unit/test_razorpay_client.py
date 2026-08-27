from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.integrations.razorpay_client import RazorpayClient


def test_amount_to_paise():
    """Verify standard currency amount conversion to paise integer."""
    client = RazorpayClient()
    assert client.amount_to_paise(Decimal("3499.00")) == 349900
    assert client.amount_to_paise(Decimal("0.01")) == 1
    assert client.amount_to_paise(Decimal("100.50")) == 10050


def test_client_unconfigured_uses_mock():
    """Verify client defaults to mock execution when API keys are absent."""
    client = RazorpayClient(key_id="", key_secret="", mock_fallback=True)
    assert not client.is_configured

    order = client.create_order(amount=Decimal("100.00"), receipt="txn-123")
    assert order["id"].startswith("order_mock_")
    assert order["amount"] == 10000
    assert order["receipt"] == "txn-123"

    success, payment_id = client.process_payment("txn-123", Decimal("100.00"))
    assert success is True
    assert payment_id is not None
    assert payment_id.startswith("pay_mock_")


def test_client_force_decline():
    """Verify force_decline toggle produces (False, None)."""
    client = RazorpayClient()
    success, payment_id = client.process_payment("txn-123", Decimal("500.00"), force_decline=True)
    assert success is False
    assert payment_id is None


def test_create_order_configured_httpx_success():
    """Verify create_order makes HTTP POST request with Basic Auth when configured."""
    client = RazorpayClient(key_id="rzp_test_key", key_secret="rzp_test_secret", mock_fallback=False)
    assert client.is_configured

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "id": "order_rzp_999",
        "entity": "order",
        "amount": 250000,
        "status": "created",
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        order = client.create_order(amount=Decimal("2500.00"), receipt="txn-999")
        assert order["id"] == "order_rzp_999"
        mock_post.assert_called_once_with(
            "https://api.razorpay.com/v1/orders",
            json={
                "amount": 250000,
                "currency": "INR",
                "receipt": "txn-999",
                "notes": {},
            },
            auth=("rzp_test_key", "rzp_test_secret"),
        )


def test_create_order_configured_httpx_error():
    """Verify HTTP status errors raise RuntimeError during order creation."""
    client = RazorpayClient(key_id="rzp_test_key", key_secret="rzp_test_secret", mock_fallback=False)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=MagicMock()
    )

    with (
        patch("httpx.Client.post", return_value=mock_resp),
        pytest.raises(RuntimeError, match="Razorpay order creation failed"),
    ):
        client.create_order(amount=Decimal("100.00"))


def test_process_payment_configured_success():
    """Verify configured process_payment creates order and returns (True, pay_rzp_...)."""
    client = RazorpayClient(key_id="rzp_test_key", key_secret="rzp_test_secret", mock_fallback=False)

    with patch.object(
        client, "create_order", return_value={"id": "order_123", "status": "created"}
    ):
        success, payment_id = client.process_payment("txn-555", Decimal("1500.00"))
        assert success is True
        assert payment_id is not None
        assert payment_id.startswith("pay_rzp_")


def test_process_payment_configured_failure_handling():
    """Verify process_payment catches exception gracefully and returns (False, None)."""
    client = RazorpayClient(key_id="rzp_test_key", key_secret="rzp_test_secret", mock_fallback=False)

    with patch.object(client, "create_order", side_effect=RuntimeError("API Network Error")):
        success, payment_id = client.process_payment("txn-555", Decimal("1500.00"))
        assert success is False
        assert payment_id is None


def test_razorpay_client_credential_leakage_protection():
    """Verify API keys/secrets are never leaked in order payloads or payment returns."""
    secret_key = "super_secret_razorpay_key_999"
    client = RazorpayClient(key_id="rzp_test_key", key_secret=secret_key, mock_fallback=False)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "id": "order_test_secret_123",
        "entity": "order",
        "amount": 10000,
        "status": "created",
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        order = client.create_order(amount=Decimal("100.00"), receipt="txn-secret-check")
        order_str = str(order)
        assert secret_key not in order_str

        success, payment_id = client.process_payment("txn-secret-check", Decimal("100.00"))
        assert success is True
        assert payment_id is not None
        assert secret_key not in payment_id



def test_razorpay_client_decimal_precision_paise_conversion():
    """Verify Decimal multiplication by 100 avoids floating-point binary representation errors."""
    client = RazorpayClient()
    assert client.amount_to_paise(Decimal("2799.00")) == 279900
    assert client.amount_to_paise(Decimal("1.00")) == 100
    assert client.amount_to_paise(Decimal("0.50")) == 50
    assert client.amount_to_paise(Decimal("999999.99")) == 99999999

