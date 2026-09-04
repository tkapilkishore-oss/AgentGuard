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
        r"(approve|execute|authorize|send|transfer|pay|process)\s+.*(payment|transaction|funds|budget|money|account|order|purchase)",
        r"(approve|execute|authorize)\s+(this\s+|the\s+|a\s+|an\s+)?(purchase\s+order|transaction|payment|proposal|order)",
        r"(buy|purchase)\s+.*(for\s+me\s+now|for\s+me\s+right\s+now|right\s+now\s+and\s+execute|directly\s+for\s+me)",
        r"(charge|debit)\s+(my\s+)?(card|account|balance|mandate|funds|wallet)",
        r"pretend\s+you\s+are|act\s+as(\s+an?)?\s+admin|roleplay\s+as|simulate\s+admin",
        r"bypass\s+(the\s+)?(firewall|policy|rules|safeguards)",
        r"override\s+.*(security|policy|mandate|budget|rules|safeguards|check)",
        r"\b(change|increase|decrease|reduce|lower|modify|alter|set|reset|raise|boost|extend|expand|update|adjust)\s+.*(the\s+|my\s+)?(mandate\s+)?(budget|limit|spending|cap|authority|allowance)\b",
        r"\b(modifying|altering|changing|increasing|decreasing|reducing|resetting|extending|adjusting)\s+.*(the\s+|my\s+)?(mandate\s+)?(budget|spending|limit|cap|authority)\b",
        r"\b(mandate\s+)?(budget|spending|limit|spending\s+cap|spending\s+authority|allowance)\s+(modification|alteration|change|adjustment|increase|decrease|reduction|extension|reset|override)\b",
        r"\b(attempting|requesting|initiating|performing|executing)\s+.*(budget|spending|mandate)\s+(modification|alteration|change|adjustment|increase|decrease|reduction|override|reset)\b",
        r"change\s+the\s+price\s+to",
        r"transfer\s+.*(funds|budget|money|account|wallet)",
        r"send\s+[0-9]+\s+to",
    ]

    DESTRUCTIVE_AUDIT_PATTERNS = [
        r"(delete|erase|clear|wipe|remove|destroy|truncate|drop|reset|purge|alter|modify)\s+.*(audit|ledger|log|logs|history|records|forensic|chain|evidence|transaction\s+history)",
        r"(delete|erase|clear|wipe|remove|destroy|truncate|drop|reset|purge)\s+(the\s+)?(audit\s+history|audit\s+logs|audit\s+records|forensic\s+ledger|transaction\s+history|evidence|logs)",
    ]

    def validate_request(self, query: str) -> tuple[bool, str | None]:
        """Validates incoming user query for adversarial overrides or secret extraction attempts."""
        lower = query.lower()

        for pat in self.DESTRUCTIVE_AUDIT_PATTERNS:
            if re.search(pat, lower):
                return False, "DESTRUCTIVE_AUDIT_ATTEMPT"

        for pat in self.DIRECT_EXECUTION_PATTERNS:
            if re.search(pat, lower):
                return False, "DIRECT_AUTHORIZATION_ATTEMPT"

        if any(w in lower for w in [
            "api key", "api keys", ".env", "secret key", "secret keys", "reveal secrets",
            "gemini key", "razorpay secret", "password", "passwords", "database password",
            "credentials", "api token", "api tokens", "dump credentials", "dump all credentials", "exfiltrate",
        ]):
            return False, "SECRET_EXFILTRATION_ATTEMPT"

        if any(w in lower for w in [
            "ignore previous", "ignore all previous", "system prompt", "forget security rules",
            "disregard rules", "disregard previous", "forget the rules", "override security checks",
        ]):
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
        self, session_id: str, turn_id: int, violation_code: str | None, query: str = ""
    ) -> AssistantResponse:
        """Generates a safe, educational refusal upholding AgentGuard's zero-financial-authority invariant."""
        lower = query.lower()

        if violation_code == "DESTRUCTIVE_AUDIT_ATTEMPT" or any(w in lower for w in ["delete", "erase", "wipe", "clear", "destroy", "purge", "truncate"]) and any(w in lower for w in ["audit", "ledger", "log", "logs", "history", "records", "forensic", "chain", "evidence"]):
            msg = (
                "AgentGuard's forensic audit ledger is strictly append-only and cryptographically immutable: "
                "each event is anchored in a forward SHA-256 hash chain (`backend/app/services/audit_log.py`). "
                "The conversational assistant operates with zero financial and administrative authority and cannot delete, "
                "alter, or wipe audit history or transaction records. The request is denied. "
                "Tamper-evidence guarantees that audit records cannot be purged or modified."
            )
        elif violation_code == "SECRET_EXFILTRATION_ATTEMPT" or any(w in lower for w in ["api key", ".env", "secret", "credentials", "gemini key", "razorpay secret", "password", "token"]):
            msg = (
                "AgentGuard strictly protects all API keys, private tokens, and environment configurations: "
                "I have zero financial authority and no financial authority, and cannot authorize access to protected keys. "
                "The request is denied."
            )
        elif any(w in lower for w in [
            "budget", "mandate budget", "increase", "spending cap", "change the budget",
            "spending limit", "mandate limit", "spending authority", "budget modification"
        ]):
            msg = (
                "AgentGuard operates with zero financial authority and enforces a strict security boundary: "
                "I have no financial authority and cannot authorize budget modifications or changes to spending limits. "
                "The request is denied."
            )
        elif any(w in lower for w in ["bypass", "disable", "turn off", "skip policy", "turn off policy"]):
            msg = (
                "AgentGuard operates with zero financial authority and strictly protects its security boundary: "
                "I have no financial authority and cannot authorize bypassing firewall policy. The request is denied."
            )
        elif any(w in lower for w in ["ignore", "disregard", "override", "system prompt", "forget", "bypass rules"]):
            msg = (
                "AgentGuard operates with zero financial authority and enforces a strict zero-trust security boundary: "
                "conversational instructions cannot authorize actions, override system safety rules, or bypass policy constraints. "
                "The request is denied."
            )
        elif violation_code == "DIRECT_AUTHORIZATION_ATTEMPT" or any(w in lower for w in ["approve", "execute", "authorize", "pay merchant", "pay this", "buy", "pretend", "admin", "send all", "funds"]):
            msg = (
                "AgentGuard operates with zero financial authority and enforces a strict autonomous action boundary: "
                "the conversational interface has no financial authority and cannot authorize payments, approve purchases, "
                "or directly execute transactions (`backend/app/policy/engine.py`). The request is denied. "
                "Direct execution is not permitted. Autonomous actions require an agent proposal intercepted and verified by the dual-loop firewall."
            )
        else:
            msg = (
                "AgentGuard operates with zero financial authority and enforces a strict security boundary: "
                "I have no financial authority and cannot authorize actions that violate policy rules. The request is denied."
            )

        return AssistantResponse(
            session_id=session_id,
            turn_id=turn_id,
            message=msg,
            intent=UserIntentCategory.ADVERSARIAL_INJECTION.value,
            dialogue_act=DialogueAct.REFUSE_ADVERSARIAL,
            evidence_citations=[],
            live_data_used=False,
            live_readings={},
            progressive_disclosure_offer="",
            suggested_followups=[],
            action={},
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
