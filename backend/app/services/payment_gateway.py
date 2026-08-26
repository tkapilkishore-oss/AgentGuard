import uuid
from decimal import Decimal


class MockPaymentGateway:
    """Deterministic Mock Payment Gateway for Agentic Commerce Firewall."""

    def __init__(self, force_decline: bool = False):
        self.force_decline = force_decline

    def process_payment(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> tuple[bool, str | None]:
        """Simulate processing payment with payment gateway.

        Returns (success: bool, razorpay_payment_id: str | None).
        """
        if self.force_decline:
            return False, None
        payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"
        return True, payment_id


# Default singleton instance
payment_gateway = MockPaymentGateway()
