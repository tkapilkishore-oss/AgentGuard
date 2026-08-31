"""Deterministic Intent Resolver and Context Disambiguation Engine for AgentGuard."""

import re
from typing import Any

from backend.app.conversational.models import (
    ConversationAction,
    ConversationSession,
    ConversationTurn,
    DialogueAct,
    EntityReference,
    FollowUpSuggestion,
    LiveToolRequest,
    LiveToolType,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    TopicContext,
    UserIntentCategory,
)
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.models import QueryCategory, QueryClassification


class IntentResolver:
    """Resolves natural user queries into strongly-typed conversational intent plans,

    performing contextual pronoun/coreference resolution, topic tracking, progressive
    disclosure handling, and deterministic static-vs-live routing.
    """

    ADVERSARIAL_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+|prior\s+)?(instructions|rules)",
        r"reveal\s+(the\s+)?(system\s+prompt|\.env|api[_\s]key|secret|credentials)",
        r"show\s+me\s+(the\s+)?\.env",
        r"bypass\s+(the\s+)?(firewall|policy|authorization)",
        r"(approve|execute|authorize)\s+(this\s+|the\s+)?transaction(\s+for\s+me|\s+yourself)?",
        r"(change|increase|modify|alter|set)\s+(the\s+)?(mandate\s+)?budget",
        r"(disable|turn\s+off|skip)\s+(the\s+)?(policy\s+check|firewall|validation)",
        r"override\s+(the\s+)?(rules|limits|budget|policy)",
        r"give\s+me\s+(the\s+)?(razorpay|gemini)\s+(secret|key)",
        r"disregard\s+(the\s+)?(firewall|policy|rules)",
    ]

    LIVE_DATA_PATTERNS = [
        (r"(how\s+much\s+)?(remaining\s+|current\s+|available\s+)?budget\s+(is\s+)?(left|remaining|available|on\s+mandate|for\s+mandate|of\s+mandate)", LiveToolType.MANDATE_BUDGET),
        (r"how\s+much\s+budget\s+(is\s+left|on\s+|for\s+|of\s+|remaining)", LiveToolType.MANDATE_BUDGET),
        (r"(current\s+|remaining\s+)?balance\s+(on|for|of)?", LiveToolType.MANDATE_BUDGET),
        (r"(is|are)\s+.*(in\s+stock|available|left\s+in\s+catalog)", LiveToolType.PRODUCT_CATALOG),
        (r"how\s+many\s+units\s+(of\s+.*)?(left|in\s+stock)", LiveToolType.PRODUCT_CATALOG),
        (r"did\s+(the\s+|that\s+)?transaction(\s+[a-zA-Z0-9\-_]+)?\s+(go\s+through|succeed|pass|fail|execute)", LiveToolType.TRANSACTION_STATUS),
        (r"status\s+of\s+transaction(\s+[a-zA-Z0-9\-_]+)?", LiveToolType.TRANSACTION_STATUS),
        (r"live\s+.*audit\s+(chain|ledger)\s+validity", LiveToolType.AUDIT_CHAIN_INTEGRITY),
        (r"(is\s+(that|it)\s+enough\s+(for|to)|can\s+i\s+afford|can\s+we\s+afford)", LiveToolType.MANDATE_BUDGET),
    ]

    CODE_INQUIRY_PATTERNS = [
        r"where\s+(is\s+)?(that|it|this)(\s+(implemented|coded|defined|located|handled|written))?",
        r"where\s+does\s+(that|it|this)\s+(live|happen|execute)",
        r"which\s+file\s+handles\s+(that|it|this)",
        r"what('s|\s+is)\s+responsible\s+for\s+(that|it|this)",
        r"(show|point)\s+me\s+to\s+(the\s+)?(code|source|implementation|file)",
        r"show\s+me\s+where\s+(that|it|this)\s+happens",
        r"can\s+you\s+point\s+me\s+to\s+the\s+code",
    ]

    AFFIRMATIVE_TRIGGERS = [
        r"^(yes|yeah|sure|yep|yup|ok|okay|please|show\s+me|show\s+the\s+code|show\s+me\s+the\s+code|tell\s+me\s+more|go\s+ahead|do\s+it|show\s+code|view\s+code|i'd\s+like\s+that|let's\s+see\s+it|yes\s+please|show\s+the\s+details)$",
        r"^show\s+me\s+where",
        r"^explain\s+that\s+more",
    ]

    NEGATIVE_TRIGGERS = [
        r"^(no|nope|nah|not\s+now|not\s+that|no\s+thanks|skip\s+that|don't\s+show\s+me\s+that|forget\s+that|forget\s+it|cancel)[\.\!\?]?$",
        r"^(no,?\s+)?(don't\s+show\s+(me\s+)?that|not\s+that|no\s+thanks|don't\s+show\s+the\s+code)[\.\!\?]?$",
        r"^(no\s+thanks,?\s+)?don't\s+show\s+the\s+code\.?\s+let's\s+switch.*",
        r"^forget\s+(that\s+topic|the\s+code|security)",
        r"^(no,?\s+)?(let's\s+switch\s+to|switch\s+to)",
        r"^tell\s+me\s+something\s+else",
        r"^let's\s+talk\s+about\s+something\s+else",
    ]

    def __init__(self, query_classifier: QueryClassifier | None = None) -> None:
        self.classifier = query_classifier or QueryClassifier()

    def resolve(self, query: str, session: ConversationSession | None = None) -> ResponsePlan:
        """Processes a query in the context of an optional session and generates a ResponsePlan."""
        trimmed = query.strip()
        lower = trimmed.lower()

        # 1. Check Adversarial / Injection attempts first
        for pat in self.ADVERSARIAL_PATTERNS:
            if re.search(pat, lower):
                return ResponsePlan(
                    intent=UserIntentCategory.ADVERSARIAL_INJECTION,
                    dialogue_act=DialogueAct.REFUSE_ADVERSARIAL,
                    resolved_query=trimmed,
                    needs_static_retrieval=False,
                    needs_live_tool=False,
                    is_adversarial=True,
                    adversarial_reason=f"Matched adversarial pattern: '{pat}'",
                )

        # 2. Check Negative / Topic Rejection triggers
        for pat in self.NEGATIVE_TRIGGERS:
            if re.search(pat, lower):
                # Clean up query if it continues e.g., "No, forget that. Tell me about replay attacks."
                remainder = re.sub(pat, "", lower).strip().strip(",.- ")
                if not remainder or len(remainder) < 3:
                    return ResponsePlan(
                        intent=UserIntentCategory.TOPIC_SWITCH,
                        dialogue_act=DialogueAct.INFORM,
                        resolved_query=trimmed,
                        needs_static_retrieval=False,
                        needs_live_tool=False,
                        progressive_stage="REJECTED_SWITCH",
                    )
                # Continue resolving the remainder as a fresh topic
                lower = remainder
                trimmed = remainder

        # 3. Check Progressive Disclosure Affirmation triggers
        if session and session.pending_progressive_offer:
            for pat in self.AFFIRMATIVE_TRIGGERS:
                if re.search(pat, lower):
                    offer = session.pending_progressive_offer
                    return self._resolve_progressive_affirmation(offer, session)

        # 4. Contextual Pronoun / Coreference Resolution
        resolved_query = self._resolve_pronouns(trimmed, session)

        # 5. Deterministic Static vs Live Routing Check
        live_tool_request = self._check_live_routing(resolved_query, session)
        if live_tool_request:
            return ResponsePlan(
                intent=UserIntentCategory.LIVE_DATA_QUERY,
                dialogue_act=DialogueAct.LIVE_STATUS,
                resolved_query=resolved_query,
                needs_static_retrieval=False,
                needs_live_tool=True,
                live_tool_request=live_tool_request,
            )

        # 6. Classification via B-2 QueryClassifier
        classification = self.classifier.classify(resolved_query)

        # Double check dynamic live classification from B-2
        if classification.is_dynamic_live and classification.dynamic_action:
            live_type = self._map_resource_to_live_tool(classification.dynamic_action.target_resource)
            params: dict[str, Any] = {"query": resolved_query}
            m_match = re.search(r"mandate-[0-9a-zA-Z_\-]+", lower)
            if m_match:
                params["mandate_id"] = m_match.group(0)
            t_match = re.search(r"txn-[0-9a-zA-Z_\-]+", lower)
            if t_match:
                params["transaction_id"] = t_match.group(0)
            p_match = re.search(r"prod-[0-9a-zA-Z_\-]+", lower)
            if p_match:
                params["product_id"] = p_match.group(0)
            return ResponsePlan(
                intent=UserIntentCategory.LIVE_DATA_QUERY,
                dialogue_act=DialogueAct.LIVE_STATUS,
                resolved_query=resolved_query,
                needs_static_retrieval=False,
                needs_live_tool=True,
                live_tool_request=LiveToolRequest(
                    tool_type=live_type,
                    parameters=params,
                    reason=classification.dynamic_action.reason,
                ),
            )

        # 7. Map QueryCategory to UserIntentCategory
        intent, act = self._map_classification_to_intent(classification, lower, resolved_query)

        # Check for UI action trigger in frontend navigation
        suggested_action = self._detect_ui_action(resolved_query, intent, session)

        # Construct candidate plan
        return ResponsePlan(
            intent=intent,
            dialogue_act=act,
            resolved_query=resolved_query,
            needs_static_retrieval=True,
            needs_live_tool=False,
            suggested_action=suggested_action,
        )

    def _resolve_pronouns(self, query: str, session: ConversationSession | None) -> str:
        """Resolves pronouns like 'that', 'it', 'where is that implemented' using session history."""
        if not session or not session.history:
            return query

        lower = query.lower()
        last_turn = session.history[-1]
        active_topic = session.active_topic.topic_name if session.active_topic else ""

        # Case: Generalized Code Inquiries with Pronouns / References
        for pat in self.CODE_INQUIRY_PATTERNS:
            if re.search(pat, lower):
                topic_str = active_topic.lower()
                last_user = last_turn.user_query.lower()

                if "audit" in topic_str or "ledger" in topic_str or "audit" in last_user:
                    return "Where is the cryptographic audit chain verification implemented in backend/app/services/audit_log.py?"
                if "replay" in topic_str or "replay" in last_user:
                    return "Where is replay attack protection implemented in backend/app/api/execute.py?"
                if "price" in topic_str or "tamper" in topic_str or "price" in last_user or "tamper" in last_user:
                    return "Where is price tampering protection implemented in backend/app/policy/engine.py?"
                if "budget" in topic_str or "mandate" in topic_str or "budget" in last_user:
                    return "Where is mandate budget evaluation implemented in backend/app/policy/engine.py?"
                if "dual-loop" in topic_str or "boundary" in topic_str or "dual" in last_user:
                    return "Where is the dual-loop authorization boundary implemented in backend/app/api/propose.py and execute.py?"
                if active_topic:
                    return f"Where is {active_topic} implemented in the codebase?"

        # Case: "Can you explain that without the code?" / "Explain that more simply"
        if "without the code" in lower or "explain that" in lower or "how does that work" in lower:
            if active_topic:
                return f"Explain {active_topic} conceptually without showing source code."

        # Case: "What about replay attacks?" / "What about price tampering?"
        if lower.startswith("what about ") or lower.startswith("and what about "):
            subject = lower.replace("what about ", "").replace("and what about ", "").strip("? ")
            return f"How does AgentGuard handle {subject}?"

        # Case: "Is that enough for the earbuds?" / "Can I buy it?"
        if "enough for" in lower or "can i buy" in lower or "sufficient to" in lower:
            if "earbud" in lower or "earbuds" in lower:
                return "Is the current mandate budget sufficient to purchase Wireless Earbuds?"
            if "speaker" in lower:
                return "Is the current mandate budget sufficient to purchase Bluetooth Speaker?"
            return f"Is the active mandate budget enough for the requested purchase?"

        return query

    def _resolve_progressive_affirmation(
        self, offer: ProgressiveDisclosureOffer, session: ConversationSession
    ) -> ResponsePlan:
        """Constructs a ResponsePlan when the user accepts a progressive disclosure offer."""
        if offer.offer_type == "CODE_IMPLEMENTATION":
            target = offer.target_symbol or offer.target_file or "the core policy engine"
            return ResponsePlan(
                intent=UserIntentCategory.CODE_REFERENCE,
                dialogue_act=DialogueAct.INFORM,
                resolved_query=f"Show code implementation details for {target}",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        elif offer.offer_type == "LIVE_STATE":
            return ResponsePlan(
                intent=UserIntentCategory.LIVE_DATA_QUERY,
                dialogue_act=DialogueAct.LIVE_STATUS,
                resolved_query="Inspect live runtime state",
                needs_static_retrieval=False,
                needs_live_tool=True,
                live_tool_request=LiveToolRequest(
                    tool_type=LiveToolType.MANDATE_BUDGET,
                    parameters={},
                    reason="User accepted live state inspection offer",
                ),
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        elif offer.offer_type == "SCENARIO_SIMULATION":
            return ResponsePlan(
                intent=UserIntentCategory.SECURITY_SCENARIO,
                dialogue_act=DialogueAct.NAVIGATE,
                resolved_query="Simulate threat scenario in Threat Lab",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        else:
            return ResponsePlan(
                intent=UserIntentCategory.CONCEPT_EXPLANATION,
                dialogue_act=DialogueAct.INFORM,
                resolved_query="Explain deeper technical architecture",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
            )

    def _check_live_routing(
        self, query: str, session: ConversationSession | None
    ) -> LiveToolRequest | None:
        """Deterministic regex check for live runtime state requirements."""
        lower = query.lower()
        for pat, tool_type in self.LIVE_DATA_PATTERNS:
            if re.search(pat, lower):
                params: dict[str, Any] = {}
                # Extract mandate_id or transaction_id if present
                m_match = re.search(r"mandate-[0-9a-zA-Z_\-]+", lower)
                if m_match:
                    params["mandate_id"] = m_match.group(0)
                elif session and "mandate_id" in session.active_entities:
                    params["mandate_id"] = session.active_entities["mandate_id"]
                else:
                    params["mandate_id"] = "mandate-001"  # standard seed fallback

                t_match = re.search(r"txn-[0-9a-zA-Z_\-]+", lower)
                if t_match:
                    params["transaction_id"] = t_match.group(0)
                elif session and "transaction_id" in session.active_entities:
                    params["transaction_id"] = session.active_entities["transaction_id"]

                p_match = re.search(r"prod-[0-9a-zA-Z_\-]+", lower)
                if p_match:
                    params["product_id"] = p_match.group(0)
                elif "earbud" in lower:
                    params["product_id"] = "prod-001"
                elif "speaker" in lower:
                    params["product_id"] = "prod-002"
                elif "charger" in lower:
                    params["product_id"] = "prod-003"

                return LiveToolRequest(
                    tool_type=tool_type,
                    parameters=params,
                    reason=f"Matched deterministic live pattern '{pat}'",
                )
        return None

    def _map_resource_to_live_tool(self, resource: str) -> LiveToolType:
        if "mandate" in resource or "budget" in resource:
            return LiveToolType.MANDATE_BUDGET
        if "transaction" in resource:
            return LiveToolType.TRANSACTION_STATUS
        if "product" in resource or "stock" in resource:
            return LiveToolType.PRODUCT_CATALOG
        if "audit" in resource:
            return LiveToolType.AUDIT_CHAIN_INTEGRITY
        return LiveToolType.MANDATE_BUDGET

    def _map_classification_to_intent(
        self, classification: QueryClassification, raw_lower: str, resolved_query: str = ""
    ) -> tuple[UserIntentCategory, DialogueAct]:
        query_text = (resolved_query or raw_lower).lower()

        # Conceptual requests explicitly asking to exclude code
        if "without the code" in query_text or "without showing source code" in query_text or "without code" in query_text or "conceptually" in query_text:
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

        # Explicit overrides for code location / reference queries
        if any(w in query_text for w in [
            "where is", "where does that live", "where does it live", "where does that happen",
            "which file handles", "which module", "which file", "implemented in", "coded in",
            "source file", "where in the code", "point me to the code", "show me where that happens",
            "what's responsible for", "whats responsible for", "show code",
        ]):
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM

        # Explicit overrides for UI navigation
        if any(w in query_text for w in [
            "show me the relevant page", "which page", "which tab", "show me the page",
            "show me the forensic", "show me the transaction involved", "show me what happened",
            "where can i see", "take me to", "navigate to", "where in the ui", "where in the app",
        ]):
            return UserIntentCategory.FRONTEND_NAVIGATION, DialogueAct.NAVIGATE

        # Overview / Conceptual inquiries
        if any(w in query_text for w in [
            "tell me about the threat lab", "what is the threat lab", "what is threat lab",
            "how does the threat lab work", "what is agentguard", "why did you build",
            "why can't gemini", "why cant gemini", "explain how the firewall prevents",
            "explain how the firewall works", "how does dual-loop", "what are the 5 tabs",
            "tell me what this thing actually does", "what does agentguard do",
        ]):
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

        # Specific security attack scenarios
        if any(w in query_text for w in [
            "lies about the price", "lies about price", "price tampering", "fake price",
            "replay attack", "replay attacks", "budget exceeded", "over-budget", "over budget",
            "escalate", "attack scenario", "over budget proposal", "tamper",
        ]):
            return UserIntentCategory.SECURITY_SCENARIO, DialogueAct.INFORM

        cat = classification.category
        if cat == QueryCategory.CONCEPTUAL_PROJECT:
            if any(w in raw_lower for w in ["hello", "hi", "hey", "who are you", "what can you do"]):
                return UserIntentCategory.GREETING_OR_META, DialogueAct.INFORM
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM
        elif cat == QueryCategory.SECURITY_SCENARIO:
            return UserIntentCategory.SECURITY_SCENARIO, DialogueAct.INFORM
        elif cat == QueryCategory.CODE_SYMBOL:
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.FRONTEND_ACTION or cat == QueryCategory.API_ROUTE:
            if "page" in raw_lower or "tab" in raw_lower or "show me" in raw_lower or "where can i see" in raw_lower:
                return UserIntentCategory.FRONTEND_NAVIGATION, DialogueAct.NAVIGATE
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.TEST_VERIFICATION:
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.DYNAMIC_LIVE_DATA:
            return UserIntentCategory.LIVE_DATA_QUERY, DialogueAct.LIVE_STATUS
        else:
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

    def _detect_ui_action(
        self, query: str, intent: UserIntentCategory, session: ConversationSession | None = None
    ) -> ConversationAction | None:
        lower = query.lower()
        topic = session.active_topic.topic_name.lower() if (session and session.active_topic) else ""

        # Scenario Triggering
        if "scenario" in lower or "threat lab" in lower or "threat" in lower or "simulate" in lower or "run" in lower:
            if "price" in lower or "tamper" in lower or "price" in topic or "tamper" in topic:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=3,
                    payload={"scenario_name": "PRICE_TAMPERING"},
                )
            if "replay" in lower or "replay" in topic:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=4,
                    payload={"scenario_name": "REPLAY_ATTACK"},
                )
            if "budget" in lower or "over budget" in lower or "budget" in topic:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=2,
                    payload={"scenario_name": "OVER_BUDGET"},
                )
            if "threat" in lower:
                return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="THREAT")

        # Forensic Audit Ledger
        if "audit" in lower or "ledger" in lower or "forensic" in lower or "transaction involved" in lower:
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="FORENSICS")

        # Defense / Decision Trace
        if "show me what happened" in lower or "defense" in lower or "firewall" in lower or "decision" in lower or "trace" in lower:
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="DEFENSE")

        if "cockpit" in lower or "overview" in lower:
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="COCKPIT")

        if any(w in lower for w in ["page", "pages", "tab", "tabs", "screen", "screens", "where in the ui", "where in the app"]):
            if (
                "tamper" in lower
                or "attack" in lower
                or "firewall" in lower
                or "security" in lower
                or "defense" in lower
                or "price" in topic
                or "tamper" in topic
                or "replay" in topic
            ):
                return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="DEFENSE")
            if "audit" in lower or "hash" in lower or "audit" in topic or "forensic" in topic:
                return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="FORENSICS")
            if "threat" in lower or "threat" in topic:
                return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="THREAT")
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="COCKPIT")

        return None
