from decimal import Decimal

from backend.app.integrations.razorpay_client import RazorpayClient


class PaymentGatewayService:
    """Payment Gateway Service delegating to RazorpayClient for Agentic Commerce Firewall."""

    def __init__(
        self,
        client: RazorpayClient | None = None,
        force_decline: bool = False,
    ) -> None:
        self.client = client or RazorpayClient()
        self.force_decline = force_decline

    def process_payment(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> tuple[bool, str | None]:
        """Process payment via Razorpay test-mode integration.

        Returns (success: bool, razorpay_payment_id: str | None).
        """
        return self.client.process_payment(
            transaction_id=transaction_id,
            amount=amount,
            force_decline=self.force_decline,
        )


# Default singleton instance maintaining Phase 2 service contract
payment_gateway = PaymentGatewayService()
