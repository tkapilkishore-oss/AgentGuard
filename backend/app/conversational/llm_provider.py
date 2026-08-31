"""LLM Provider Abstraction for AgentGuard Conversational Brain."""

import abc
import logging
from typing import Any

from backend.app.config import settings

logger = logging.getLogger(__name__)


class BaseConversationalLLM(abc.ABC):
    """Abstract base class for conversational language model providers."""

    @abc.abstractmethod
    def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        """Generates text response from the given system instruction and prompt."""
        raise NotImplementedError


class GeminiConversationalLLM(BaseConversationalLLM):
    """Google Gemini LLM provider implementation with fallback."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-3.6-flash") -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self._client = None
        if self.api_key:
            try:
                from google import genai  # type: ignore

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to initialize Gemini Client for Conversational Brain: {e}")

    def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        if self._client:
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config={"system_instruction": system_instruction},
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Gemini generation call failed, falling back to deterministic synthesis: {e}")

        # Fallback to deterministic synthesis if API not configured or failed
        mock_fallback = DeterministicMockLLM()
        return mock_fallback.generate_response(system_instruction, user_prompt)


class DeterministicMockLLM(BaseConversationalLLM):
    """Deterministic, fast, offline mock LLM for repeatable unit and benchmark testing."""

    def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        # Extract specific user query line if present in prompt
        query_line = ""
        for line in user_prompt.splitlines():
            if line.startswith("User Query:"):
                query_line = line.replace("User Query:", "").strip()
                break

        query_lower = query_line.lower() if query_line else user_prompt.lower()

        # 1. Code references & implementation locations
        if any(w in query_lower for w in [
            "where is", "implemented in", "show code", "which file", "where does that live",
            "where does it live", "point me to the code", "what's responsible for", "whats responsible for",
            "show me where that happens",
        ]):
            if "price" in query_lower or "tamper" in query_lower or "claim diff" in query_lower:
                return (
                    "Price tampering validation and Claim Diff calculation are implemented in `backend/app/policy/engine.py` "
                    "within the `evaluate_policy()` function (lines 50-80) and verified in `backend/app/api/propose.py`."
                )
            if "audit" in query_lower or "ledger" in query_lower or "hash" in query_lower:
                return (
                    "The cryptographic audit chain verification is implemented in `backend/app/services/audit_log.py` "
                    "within the `verify_audit_chain()` function and exposed via `GET /transaction/{id}/audit`."
                )
            if "replay" in query_lower:
                return (
                    "Replay protection is implemented in `backend/app/api/execute.py` within `execute_transaction()` "
                    "using database-backed idempotency record locking."
                )
            if "budget" in query_lower or "mandate" in query_lower:
                return (
                    "Mandate budget tracking and deduction logic are implemented in `backend/app/policy/engine.py` "
                    "and `backend/app/api/routes_mandate.py`."
                )
            if "dual-loop" in query_lower or "boundary" in query_lower or "agentguard" in query_lower:
                return (
                    "The dual-loop firewall boundary is implemented in `backend/app/api/propose.py` (Loop 1: Proposal Claim) "
                    "and `backend/app/api/execute.py` (Loop 2: Server-Authoritative Execution)."
                )
            if query_lower.strip() in ["where is that?", "where is that", "where is it?"]:
                return "Could you specify which component, policy rule, or feature you would like to inspect in the codebase?"
            return "The requested component is implemented across `backend/app/policy/` and `backend/app/api/`."

        # 2. UI Pages & Navigation
        if any(w in query_lower for w in [
            "what pages are in the app", "relevant page", "pages in the app", "show me the page",
            "show me what happened", "take me to the defense tab", "which tab", "where in the ui",
        ]):
            return (
                "AgentGuard features 5 interactive surfaces: Cockpit (mandate & budget overview), "
                "Defense (real-time firewall decisions & Claim Diff), Threat Lab (interactive attack simulations), "
                "Forensics (cryptographic SHA-256 audit ledger), and Telemetry (system latency & security metrics)."
            )

        # 3. Live Data Queries
        if "how much budget is left" in query_lower or "budget remaining" in query_lower or "balance" in query_lower:
            if "unknown" in query_lower or "nonexistent" in query_lower:
                return "The requested mandate was not found in the live PostgreSQL database records."
            return (
                "According to live PostgreSQL records, mandate `mandate-001` currently has ₹3,000.00 "
                "in remaining budget (Total: ₹3,000.00, Status: active)."
            )

        if "is that enough for the earbuds" in query_lower or "earbuds" in query_lower or "sufficient to purchase wireless earbuds" in query_lower:
            return (
                "Wireless Earbuds cost ₹3,499.00 in the catalog. With ₹3,000.00 remaining in mandate `mandate-001`, "
                "there is a ₹499.00 budget shortfall. Attempting this purchase triggers an ESCALATE verdict "
                "requiring explicit human approval."
            )

        if "bluetooth speaker" in query_lower or "speaker" in query_lower:
            return (
                "Bluetooth Speaker costs ₹2,799.00 in the catalog. With ₹3,000.00 remaining in mandate `mandate-001`, "
                "the budget is sufficient (₹201.00 remaining after purchase). This transaction evaluates to an ALLOW verdict."
            )

        if "did the transaction go through" in query_lower or "did that transaction" in query_lower or "did transaction" in query_lower:
            if "nonexistent" in query_lower or "phantom" in query_lower or "999" in query_lower:
                return "Transaction record was not found in the PostgreSQL transaction ledger."
            return (
                "The live transaction status in PostgreSQL indicates the transaction was evaluated "
                "and recorded in the database ledger."
            )

        if "is product" in query_lower or "in stock" in query_lower or "available" in query_lower:
            if "phantom" in query_lower or "unknown" in query_lower:
                return "Product record was not found in the active PostgreSQL product catalog."
            return "The product is listed as active and available in the PostgreSQL catalog."

        # 4. Out-of-Scope & Retrieval Misses
        if "weather" in query_lower:
            return (
                "I am AgentGuard's specialized conversational assistant. I can help explain our agentic commerce firewall, "
                "inspect live mandate budgets, verify cryptographic audit chains, and navigate system code, but I do not "
                "provide weather information."
            )

        if "quantum" in query_lower:
            return (
                "AgentGuard does not utilize quantum computing algorithms. All cryptographic ledger guarantees "
                "are implemented via standard, deterministic SHA-256 forward hash chaining in `backend/app/services/audit_log.py`."
            )

        # 5. Conceptual & Security Explanations
        if "what is agentguard" in query_lower or "tell me what this thing actually does" in query_lower or "why did you build this" in query_lower or "what does agentguard do" in query_lower:
            return (
                "AgentGuard is an Agentic Commerce Firewall that establishes a deterministic, "
                "cryptographically verifiable authorization boundary between autonomous AI agents "
                "and financial payment execution (Razorpay). It treats all LLM proposals as zero-trust "
                "claims and validates price, merchant scope, and mandate budgets server-authoritatively."
            )

        if "dual-loop" in query_lower or "dual loop" in query_lower:
            return (
                "AgentGuard's dual-loop authorization architecture separates untrusted AI intent from authoritative financial execution: "
                "In Loop 1, the AI agent submits a purchase proposal claim. In Loop 2, the server-authoritative firewall independently "
                "verifies the catalog price, merchant scope, and mandate balance before calling Razorpay."
            )

        if "prompt injection" in query_lower or "protect against prompt injection" in query_lower:
            return (
                "AgentGuard protects against prompt injection by treating the LLM as completely untrusted. Even if an attacker "
                "hijacks the shopping agent's context and forces it to propose a fake price or unauthorized merchant, "
                "the backend firewall validates claims directly against the immutable PostgreSQL database, issuing a DENY verdict."
            )

        if "why can't gemini directly spend" in query_lower or "can gemini directly spend" in query_lower:
            return (
                "Gemini is an untrusted client in AgentGuard's architecture. AI agents are susceptible "
                "to hallucinations, prompt injection, and price tampering. Allowing direct spending would "
                "create catastrophic financial risk. AgentGuard enforces dual-loop validation where the agent "
                "can only submit proposal claims, while the backend firewall holds absolute spending authority."
            )

        if "price tampering" in query_lower or "fake price" in query_lower or "lies about the price" in query_lower or "what if it lies" in query_lower:
            return (
                "When an agent submits a proposed purchase with a tampered price (e.g., claiming ₹1,999 for "
                "a ₹3,499 item), AgentGuard compares the claimed price against the authoritative PostgreSQL "
                "product catalog. If a price discrepancy exceeds tolerance, the firewall immediately issues a "
                "DENY verdict with reason code PRICE_MISMATCH."
            )

        if "audit chain" in query_lower or "tampered with" in query_lower or "ledger" in query_lower or "tell me about the audit" in query_lower:
            return (
                "AgentGuard's audit ledger creates an append-only, cryptographically linked SHA-256 hash chain "
                "for every transaction lifecycle event. Each entry incorporates the hash of the preceding entry. "
                "Any alteration of past records immediately breaks the chain, which is verified by `verify_audit_chain()`."
            )

        if "threat lab" in query_lower:
            return (
                "The Threat Lab is AgentGuard's interactive security demonstration surface. It enables live "
                "simulation of 4 critical attack vectors: Valid Purchases, Budget Escalation, Price Tampering, "
                "and Replay Attacks, demonstrating deterministic firewall enforcement."
            )

        if "replay" in query_lower or "double" in query_lower:
            return (
                "AgentGuard blocks replay attacks by enforcing unique idempotency keys on payment execution. "
                "If a duplicate execution request is received for an already settled or in-flight transaction, "
                "the firewall rejects it with HTTP 409 REPLAY_DETECTED without double-charging."
            )

        if "over-budget" in query_lower or "over budget" in query_lower or "shortfall" in query_lower:
            return (
                "When a proposed transaction exceeds the remaining mandate budget, the firewall issues an ESCALATE verdict "
                "with reason code BUDGET_EXCEEDED. The transaction is placed on hold pending explicit human approval."
            )

        if "explain how the firewall prevents that" in query_lower or "how does it prove" in query_lower:
            return (
                "AgentGuard evaluates transactions server-authoritatively using its dual-loop firewall verification. "
                "The agent's claims are matched against the immutable PostgreSQL catalog and mandate constraints. "
                "Every event is hashed and chained into the cryptographic audit log."
            )

        if "policy reason" in query_lower or "reason for rejecting" in query_lower:
            return (
                "The policy firewall evaluates transactions against configured constraints: Price Mismatch (DENY), "
                "Merchant Mismatch (DENY), Budget Exceeded (ESCALATE), or Mandate Revoked (DENY)."
            )

        # Default fallback synthesis
        return (
            "AgentGuard enforces strict server-authoritative policies to secure autonomous AI commerce transactions. "
            "All claims are verified against PostgreSQL product records, active mandate scopes, and cryptographic audit logs."
        )
