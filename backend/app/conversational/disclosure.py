"""Contextual Progressive Disclosure Engine for AgentGuard."""

from backend.app.conversational.models import (
    ConversationAction,
    ConversationSession,
    ConversationalPurpose,
    FollowUpSuggestion,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    ResponseStrategy,
    UserIntentCategory,
)


class ProgressiveDisclosureEngine:
    """Generates contextual, purpose-driven progressive disclosure offers and follow-up suggestions

    without formulaic sentence repetition.
    """

    def evaluate_disclosure(
        self, plan: ResponsePlan, session: ConversationSession | None
    ) -> tuple[ProgressiveDisclosureOffer | None, list[FollowUpSuggestion]]:
        """Evaluates whether a progressive disclosure offer is appropriate and crafts tailored follow-up suggestions."""
        # 1. Suppress offers for adversarial, greeting, out-of-scope, or direct follow-up acceptance
        if plan.intent in (
            UserIntentCategory.ADVERSARIAL_INJECTION,
            UserIntentCategory.GREETING_OR_META,
            UserIntentCategory.OUT_OF_SCOPE,
        ) or plan.purpose in (
            ConversationalPurpose.ADVERSARIAL,
            ConversationalPurpose.OUT_OF_SCOPE,
        ):
            return None, []

        if plan.progressive_stage == "FOLLOWUP_ACCEPTED":
            return None, self._generate_related_suggestions(plan)

        query_lower = plan.resolved_query.lower()
        offer: ProgressiveDisclosureOffer | None = None
        suggestions: list[FollowUpSuggestion] = []

        # 2. Topic-Specific Code & Live State Offers
        if "price" in query_lower or "tamper" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="evaluate_policy",
                target_file="backend/app/policy/engine.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/policy/engine.py", "symbol": "evaluate_policy"},
                ),
                prompt_text="I can show you where price tampering validation is implemented in the codebase if desired.",
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

        elif "audit" in query_lower or "ledger" in query_lower or "hash" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="verify_audit_chain",
                target_file="backend/app/services/audit_log.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/services/audit_log.py", "symbol": "verify_audit_chain"},
                ),
                prompt_text="I can show you how the SHA-256 hash chaining is cryptographically verified in the code if desired.",
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

        elif "replay" in query_lower or "duplicate" in query_lower:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="execute_transaction",
                target_file="backend/app/api/execute.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/api/execute.py", "symbol": "execute_transaction"},
                ),
                prompt_text="I can show you where the idempotency lock is verified in the execution endpoint if desired.",
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

        # 3. Strategy-Tailored Conceptual & Structural Offers
        elif plan.strategy == ResponseStrategy.INTRODUCE or plan.purpose == ConversationalPurpose.INFORMATION_REQUEST:
            offer = ProgressiveDisclosureOffer(
                offer_type="OPERATIONAL_FLOW",
                prompt_text="Want to see what happens when an AI agent proposes a purchase?",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Operational Flow",
                    query="What does AgentGuard actually do in practice?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Understand step-by-step transaction interception.",
                ),
                FollowUpSuggestion(
                    label="Why AgentGuard?",
                    query="Why would anyone actually need this architecture?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Explore the autonomous AI security gap.",
                ),
                FollowUpSuggestion(
                    label="Threat Scenarios",
                    query="Tell me about the Threat Lab scenarios",
                    intent_target=UserIntentCategory.SECURITY_SCENARIO,
                    rationale="Review the 4 core security invariants.",
                ),
            ]

        elif plan.strategy == ResponseStrategy.EXPLAIN_FUNCTION or plan.purpose == ConversationalPurpose.FUNCTIONAL_EXPLANATION:
            offer = ProgressiveDisclosureOffer(
                offer_type="CONCRETE_EXAMPLE",
                prompt_text="Want to see a concrete example such as a price tampering attack?",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Real Example",
                    query="Give me a real example.",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Walk through an adversarial price tampering scenario.",
                ),
                FollowUpSuggestion(
                    label="Gateway Comparison",
                    query="What's the real advantage over a normal payment gateway?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Contrast standard gateways with AgentGuard.",
                ),
                FollowUpSuggestion(
                    label="Dual-Loop Mechanism",
                    query="How does the dual-loop verification flow work?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Inspect the Loop 1 / Loop 2 boundary.",
                ),
            ]

        elif plan.strategy == ResponseStrategy.EXPLAIN_WHY or plan.purpose == ConversationalPurpose.VALUE_PROPOSITION:
            offer = ProgressiveDisclosureOffer(
                offer_type="COMPARISON",
                prompt_text="Want me to compare AgentGuard with a standard payment gateway such as Razorpay?",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Gateway Comparison",
                    query="What's the real advantage over just using a normal payment gateway?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Understand untrusted client vs standard gateway.",
                ),
                FollowUpSuggestion(
                    label="Concrete Example",
                    query="Give me a real example.",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="See how price tampering is caught in real-time.",
                ),
                FollowUpSuggestion(
                    label="Threat Lab",
                    query="Show me the Threat Lab",
                    intent_target=UserIntentCategory.FRONTEND_NAVIGATION,
                    rationale="Simulate live attack vectors.",
                ),
            ]

        elif plan.strategy == ResponseStrategy.DIFFERENTIATE or plan.purpose == ConversationalPurpose.COMPARISON:
            offer = ProgressiveDisclosureOffer(
                offer_type="DUAL_LOOP_FLOW",
                prompt_text="Want me to walk through the dual-loop verification mechanism?",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="Dual-Loop Verification",
                    query="How does the dual-loop verification flow work?",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Understand the two-stage authorization boundary.",
                ),
                FollowUpSuggestion(
                    label="Price Tampering Example",
                    query="Give me a concrete example of price tampering.",
                    intent_target=UserIntentCategory.CONCEPT_EXPLANATION,
                    rationale="Review a concrete attack walkthrough.",
                ),
                FollowUpSuggestion(
                    label="Check Live Budget",
                    query="How much budget is left right now?",
                    intent_target=UserIntentCategory.LIVE_DATA_QUERY,
                    rationale="Fetch active balance from PostgreSQL.",
                ),
            ]

        elif plan.strategy == ResponseStrategy.GIVE_EXAMPLE or plan.purpose == ConversationalPurpose.EXAMPLE_REQUEST:
            offer = ProgressiveDisclosureOffer(
                offer_type="CODE_IMPLEMENTATION",
                target_symbol="evaluate_policy",
                target_file="backend/app/policy/engine.py",
                target_action=ConversationAction(
                    action_type="HIGHLIGHT_CODE",
                    payload={"file": "backend/app/policy/engine.py", "symbol": "evaluate_policy"},
                ),
                prompt_text="Want to see where this policy check is implemented in the Python codebase?",
            )
            suggestions = [
                FollowUpSuggestion(
                    label="View Policy Code",
                    query="Where is that protection implemented?",
                    intent_target=UserIntentCategory.CODE_REFERENCE,
                    rationale="Inspect evaluate_policy() in engine.py.",
                ),
                FollowUpSuggestion(
                    label="Threat Lab Simulation",
                    query="Show me the price tampering attack in Threat Lab",
                    intent_target=UserIntentCategory.FRONTEND_NAVIGATION,
                    rationale="Simulate price tampering in the interactive UI.",
                ),
                FollowUpSuggestion(
                    label="Replay Protection",
                    query="What about replay attacks?",
                    intent_target=UserIntentCategory.SECURITY_SCENARIO,
                    rationale="Explore duplicate execution prevention.",
                ),
            ]

        else:
            suggestions = self._generate_related_suggestions(plan)

        # 4. Suppress duplicate offers already presented in this session
        if offer and session:
            if offer.prompt_text in session.offers_already_made:
                # Do not repeat identical offer text
                offer = None
            else:
                session.offers_already_made.append(offer.prompt_text)

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
