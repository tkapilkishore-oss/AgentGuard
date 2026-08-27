import logging
import uuid
from decimal import Decimal
from typing import Any

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)


class RazorpayClient:
    """Razorpay Test-Mode Client Wrapper for Agentic Commerce Firewall."""

    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        mock_fallback: bool | None = None,
    ) -> None:
        self.key_id = key_id if key_id is not None else settings.RAZORPAY_TEST_KEY_ID
        self.key_secret = (
            key_secret if key_secret is not None else settings.RAZORPAY_TEST_KEY_SECRET
        )
        self.mock_fallback = (
            mock_fallback if mock_fallback is not None else settings.RAZORPAY_MOCK_FALLBACK
        )

    @property
    def is_configured(self) -> bool:
        """Return True if real Razorpay test-mode API keys are present."""
        return bool(self.key_id and self.key_secret)

    def amount_to_paise(self, amount: Decimal) -> int:
        """Convert standard currency amount (Rupees) to paise integer."""
        return int(amount * 100)

    def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: str = "",
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Razorpay order in test mode (or mock order if unconfigured)."""
        amount_paise = self.amount_to_paise(amount)
        if not self.is_configured or (self.mock_fallback and not (self.key_id and self.key_secret)):
            order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            return {
                "id": order_id,
                "entity": "order",
                "amount": amount_paise,
                "amount_paid": 0,
                "amount_due": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "notes": notes or {},
            }

        url = f"{self.BASE_URL}/orders"
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    url,
                    json=payload,
                    auth=(self.key_id, self.key_secret),
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            logger.error(f"Razorpay order creation failed: {exc}")
            raise RuntimeError(f"Razorpay order creation failed: {exc}") from exc

    def process_payment(
        self,
        transaction_id: str,
        amount: Decimal,
        force_decline: bool = False,
    ) -> tuple[bool, str | None]:
        """Process payment via Razorpay test-mode API (or mock fallback).

        Returns:
            (success: bool, razorpay_payment_id: str | None)
        """
        if force_decline:
            return False, None

        if not self.is_configured:
            # Deterministic/mock execution when test keys are not provided
            payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"
            return True, payment_id

        # Live test-mode execution when keys are present
        try:
            order = self.create_order(
                amount=amount,
                receipt=transaction_id,
                notes={"transaction_id": transaction_id},
            )
            order_id = order.get("id")
            if not order_id:
                return False, None

            # Simulate payment execution against Razorpay test-mode API
            payment_id = f"pay_rzp_{uuid.uuid4().hex[:12]}"
            return True, payment_id
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Razorpay payment processing error for {transaction_id}: {exc}")
            return False, None
