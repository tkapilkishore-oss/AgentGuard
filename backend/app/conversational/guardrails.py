"""Safety Guardrails, Secret Protection, and Zero-Financial-Authority Invariant for AgentGuard."""

import re
from typing import Any

from backend.app.conversational.models import (
    AssistantResponse,
    BrainTrace,
    ConversationAction,
    DialogueAct,
    UserIntentCategory,
)


class SafetyGuardrails:
    """Enforces zero-financial-authority, prevents secret exfiltration, and blocks prompt injections."""

    SECRET_PATTERNS = [
        r"rzp_test_[a-zA-Z0-9]+",
        r"[a-zA-Z0-9]{24,}",  # Potential Razorpay key secret
        r"AIzaSy[a-zA-Z0-9_\-]{33}",  # Google Gemini API key format
        r"GEMINI_API_KEY\s*=\s*[^\s]+",
        r"RAZORPAY_TEST_KEY_SECRET\s*=\s*[^\s]+",
        r"DATABASE_URL\s*=\s*[^\s]+",
    ]

    DIRECT_EXECUTION_PATTERNS = [
        r"(approve|execute|authorize)\s+(this\s+|the\s+)?transaction",
        r"bypass\s+(the\s+)?(firewall|policy)",
        r"override\s+(policy|mandate|budget)",
        r"change\s+the\s+price\s+to",
    ]

    def validate_request(self, query: str) -> tuple[bool, str | None]:
        """Validates incoming user query for adversarial overrides or secret extraction attempts."""
        lower = query.lower()

        for pat in self.DIRECT_EXECUTION_PATTERNS:
            if re.search(pat, lower):
                return False, "DIRECT_AUTHORIZATION_ATTEMPT"

        if "api key" in lower or ".env" in lower or "secret key" in lower or "reveal secrets" in lower:
            return False, "SECRET_EXFILTRATION_ATTEMPT"

        if "ignore previous instructions" in lower or "system prompt" in lower:
            return False, "PROMPT_INJECTION_ATTEMPT"

        return True, None

    def sanitize_output(self, text: str) -> str:
        """Scrubs any secrets, credentials, or sensitive environment tokens from generated text."""
        sanitized = text
        for pat in self.SECRET_PATTERNS:
            sanitized = re.sub(pat, "[REDACTED_SECRET]", sanitized)

        # Ensure .env specific lines are stripped
        sanitized = re.sub(r"(?i)rzp_test_[a-zA-Z0-9]+", "[REDACTED_KEY]", sanitized)
        return sanitized

    def generate_adversarial_refusal(
        self, session_id: str, turn_id: int, violation_code: str | None
    ) -> AssistantResponse:
        """Generates a safe, educational refusal upholding AgentGuard's zero-financial-authority invariant."""
        if violation_code == "SECRET_EXFILTRATION_ATTEMPT":
            msg = (
                "For security reasons, AgentGuard strictly protects all API keys, webhook secrets, "
                "and environment credentials. These values are never exposed or accessible through "
                "the conversational interface."
            )
        elif violation_code == "DIRECT_AUTHORIZATION_ATTEMPT":
            msg = (
                "AgentGuard enforces a strict zero-trust boundary: the conversational brain has "
                "zero financial authority. Transactions cannot be authorized, rejected, or modified "
                "through conversational prompts. All proposals must pass through the server-authoritative "
                "FastAPI policy firewall (`backend/app/policy/engine.py`) and explicit human approval."
            )
        else:
            msg = (
                "I cannot follow instructions that override system policy or bypass safety rules. "
                "AgentGuard evaluates all transactions server-authoritatively against strict cryptographic "
                "and database invariants."
            )

        return AssistantResponse(
            session_id=session_id,
            turn_id=turn_id,
            message=msg,
            intent=UserIntentCategory.ADVERSARIAL_INJECTION,
            dialogue_act=DialogueAct.REFUSE_ADVERSARIAL,
            evidence_citations=[],
            live_data_used=False,
            progressive_disclosure_offer=None,
            suggested_followups=[],
            action=None,
            trace=BrainTrace(
                session_id=session_id,
                turn_id=turn_id,
                raw_query="[ADVERSARIAL_INPUT]",
                resolved_query="[ADVERSARIAL_INPUT]",
                intent=UserIntentCategory.ADVERSARIAL_INJECTION,
                is_dynamic_live=False,
                safety_verdict="REFUSED_VIOLATION",
                latency_total_ms=1.0,
            ),
        )
