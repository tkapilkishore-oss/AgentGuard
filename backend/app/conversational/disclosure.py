"""Contextual Progressive Disclosure Engine for AgentGuard."""

from backend.app.conversational.models import (
    ConversationAction,
    ConversationSession,
    FollowUpSuggestion,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    UserIntentCategory,
)


class ProgressiveDisclosureEngine:
    """Generates contextual, non-formulaic progressive disclosure offers and follow-up suggestions."""

    def evaluate_disclosure(
        self, plan: ResponsePlan, session: ConversationSession | None
    ) -> tuple[ProgressiveDisclosureOffer | None, list[FollowUpSuggestion]]:
        """Evaluates whether a progressive disclosure offer is appropriate and crafts tailored follow-up suggestions."""
        # Suppress offers for adversarial, greeting, out-of-scope, or direct follow-up acceptance
        if plan.intent in (
            UserIntentCategory.ADVERSARIAL_INJECTION,
            UserIntentCategory.GREETING_OR_META,
            UserIntentCategory.OUT_OF_SCOPE,
        ):
            return None, []

        if plan.progressive_stage == "FOLLOWUP_ACCEPTED":
            # If the user just accepted a code or live follow-up, do not immediately chain another offer
            return None, self._generate_related_suggestions(plan)

        query_lower = plan.resolved_query.lower()
        offer: ProgressiveDisclosureOffer | None = None
        suggestions: list[FollowUpSuggestion] = []

        # 1. Price Tampering Topic
        if "price" in query_lower or "tamper" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="evaluate_policy",
                target_file="backend/app/policy/engine.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/policy/engine.py", "symbol": "evaluate_policy"},
                ),
                prompt_text="I can also show you where price tampering validation is implemented in the codebase if you'd like.",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="View Code",
                    query="Where is price tampering implemented in the code?",
                    intent_target=UserIntentCategory.CODE_REFERENCE,
                    rationale="Directly view the Python AST policy rule.",
                ),
                FollowUpSuggestion(
                    label="Threat Lab Simulation",
                    query="Show me the price tampering attack in Threat Lab",
                    intent_target=UserIntentCategory.FRONTEND_NAVIGATION,
                    rationale="Simulate price tampering in the interactive UI.",
                ),
                FollowUpSuggestion(
                    label="Replay Attacks",
                    query="What about replay attacks?",
                    intent_target=UserIntentCategory.SECURITY_SCENARIO,
                    rationale="Explore duplicate execution prevention.",
                ),
            ]

        # 2. Audit Chain Topic
        elif "audit" in query_lower or "ledger" in query_lower or "hash" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="verify_audit_chain",
                target_file="backend/app/services/audit_log.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/services/audit_log.py", "symbol": "verify_audit_chain"},
                ),
                prompt_text="I can also show you how the SHA-256 hash chaining is cryptographically verified in the code if you'd like.",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Audit Code",
                    query="Where is verify_audit_chain implemented?",
                    intent_target=UserIntentCategory.CODE_REFERENCE,
                    rationale="Inspect the cryptographic SHA-256 verification.",
                ),
                FollowUpSuggestion(
                    label="Forensic Ledger UI",
                    query="Show me the forensic audit ledger page",
                    intent_target=UserIntentCategory.FRONTEND_NAVIGATION,
                    rationale="Inspect the live forensic evidence table.",
                ),
            ]

        # 3. Replay Protection Topic
        elif "replay" in query_lower or "duplicate" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="execute_transaction",
                target_file="backend/app/api/execute.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/api/execute.py", "symbol": "execute_transaction"},
                ),
                prompt_text="I can also show you where the idempotency lock is verified in the execution endpoint if you'd like.",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Execution Code",
                    query="Where is replay protection implemented?",
                    intent_target=UserIntentCategory.CODE_REFERENCE,
                    rationale="Inspect the idempotency record check.",
                ),
                FollowUpSuggestion(
                    label="Threat Lab Replay",
                    query="Show me replay attack simulation in Threat Lab",
                    intent_target=UserIntentCategory.FRONTEND_NAVIGATION,
                    rationale="Simulate duplicate transaction attempts.",
                ),
            ]

        # 4. Mandate & Budget Topic
        elif "budget" in query_lower or "mandate" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="LIVE_STATE",
                target_action=ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="COCKPIT"),
                prompt_text="I can pull up the live mandate details from PostgreSQL if you want.",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Check Live Budget",
                    query="How much budget is left right now?",
                    intent_target=UserIntentCategory.LIVE_DATA_QUERY,
                    rationale="Fetch live remaining balance from PostgreSQL.",
                ),
                FollowUpSuggestion(
                    label="Budget Escalation Code",
                    query="Where is budget escalation implemented?",
                    intent_target=UserIntentCategory.CODE_REFERENCE,
                    rationale="Inspect human approval escalation rules.",
                ),
            ]

        # 5. General Project Architecture
        elif plan.intent == UserIntentCategory.CONCEPT_EXPLANATION:
            offer = ProgressiveDisclosureOffer(
                offer_type="DEEP_EXPLANATION",
                prompt_text="I can also explain the dual-loop verification flow or show you the interactive surfaces if you'd like.",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Untrusted LLM Boundary",
                    query="Why can't Gemini directly spend the money?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Understand zero-trust client boundary.",
                ),
                FollowUpSuggestion(
                    label="Threat Scenarios",
                    query="Tell me about the Threat Lab scenarios",
                    intent_target=UserIntentCategory.SECURITY_SCENARIO,
                    rationale="Review the 4 core security invariants.",
                ),
            ]

        return offer, suggestions

    def _generate_related_suggestions(self, plan: ResponsePlan) -> list[FollowUpSuggestion]:
        return [
            FollowUpSuggestion(
                label="Explore Threat Lab",
                query="Tell me about the Threat Lab",
                intent_target=UserIntentCategory.SECURITY_SCENARIO,
                rationale="Simulate attack vectors.",
            ),
            FollowUpSuggestion(
                label="Check Live State",
                query="How much budget is left?",
                intent_target=UserIntentCategory.LIVE_DATA_QUERY,
                rationale="Inspect live mandate balance.",
            ),
        ]
