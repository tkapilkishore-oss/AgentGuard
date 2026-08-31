"""Lightweight Query Classifier and Entity Extractor for Retrieval Routing."""

import re

from backend.app.knowledge.models import DomainCategory, SourceTier
from backend.app.retrieval.models import (
    DynamicLiveAction,
    QueryCategory,
    QueryClassification,
)


class QueryClassifier:
    """Classifies user queries into retrieval intents and extracts structured entity hints."""

    # Known code symbols in the AgentGuard codebase and their associated primary domains
    KNOWN_SYMBOLS = [
        "evaluate_policy",
        "PolicyEngine",
        "verify_proposal",
        "_check_price",
        "_check_merchant",
        "_check_budget",
        "_check_mandate",
        "PolicyDecision",
        "PolicyViolation",
        "AuditLog",
        "append_event",
        "verify_chain",
        "get_events_for_transaction",
        "compute_event_hash",
        "RazorpayClient",
        "create_order",
        "verify_payment_signature",
        "fetch_payment",
        "RazorpayService",
        "execute_payment",
        "ProposalRequest",
        "ProposalResponse",
        "ExecuteRequest",
        "ExecuteResponse",
        "ApproveRequest",
        "Mandate",
        "Transaction",
        "AuditEvent",
        "Product",
        "IdempotencyRecord",
        "GeminiAgent",
        "RetrievalEngine",
    ]

    SYMBOL_DOMAIN_MAP: dict[str, DomainCategory] = {
        "evaluate_policy": DomainCategory.I_POLICY_ENGINE,
        "PolicyEngine": DomainCategory.I_POLICY_ENGINE,
        "verify_proposal": DomainCategory.I_POLICY_ENGINE,
        "_check_price": DomainCategory.I_POLICY_ENGINE,
        "_check_merchant": DomainCategory.I_POLICY_ENGINE,
        "_check_budget": DomainCategory.I_POLICY_ENGINE,
        "_check_mandate": DomainCategory.I_POLICY_ENGINE,
        "PolicyDecision": DomainCategory.I_POLICY_ENGINE,
        "PolicyViolation": DomainCategory.I_POLICY_ENGINE,
        "AuditLog": DomainCategory.P_AUDIT_TRAIL,
        "append_event": DomainCategory.P_AUDIT_TRAIL,
        "verify_chain": DomainCategory.P_AUDIT_TRAIL,
        "get_events_for_transaction": DomainCategory.P_AUDIT_TRAIL,
        "compute_event_hash": DomainCategory.Q_SHA256_HASH_CHAIN,
        "RazorpayClient": DomainCategory.M_RAZORPAY_INTEGRATION,
        "create_order": DomainCategory.M_RAZORPAY_INTEGRATION,
        "verify_payment_signature": DomainCategory.M_RAZORPAY_INTEGRATION,
        "fetch_payment": DomainCategory.M_RAZORPAY_INTEGRATION,
        "RazorpayService": DomainCategory.M_RAZORPAY_INTEGRATION,
        "execute_payment": DomainCategory.M_RAZORPAY_INTEGRATION,
        "ProposalRequest": DomainCategory.G_BACKEND_ARCHITECTURE,
        "ProposalResponse": DomainCategory.G_BACKEND_ARCHITECTURE,
        "ExecuteRequest": DomainCategory.G_BACKEND_ARCHITECTURE,
        "ExecuteResponse": DomainCategory.G_BACKEND_ARCHITECTURE,
        "ApproveRequest": DomainCategory.G_BACKEND_ARCHITECTURE,
        "Mandate": DomainCategory.J_MANDATES,
        "Transaction": DomainCategory.L_TRANSACTIONS,
        "AuditEvent": DomainCategory.P_AUDIT_TRAIL,
        "Product": DomainCategory.L_TRANSACTIONS,
        "IdempotencyRecord": DomainCategory.L_TRANSACTIONS,
        "GeminiAgent": DomainCategory.N_AGENT_BEHAVIOR,
        "RetrievalEngine": DomainCategory.G_BACKEND_ARCHITECTURE,
    }

    # Known API Routes
    KNOWN_ROUTES = [
        ("POST", "/transaction/propose"),
        ("POST", "/transaction/execute"),
        ("POST", "/transaction/{id}/approve"),
        ("POST", "/transaction/{id}/reject"),
        ("GET", "/transaction/{id}"),
        ("GET", "/mandate/{id}"),
        ("POST", "/mandate/{id}/revoke"),
        ("GET", "/products"),
        ("POST", "/agent/chat"),
        ("GET", "/audit/chain"),
        ("GET", "/audit/verify"),
        ("GET", "/audit/transactions"),
        ("GET", "/audit/transaction/{id}"),
        ("GET", "/health"),
    ]

    # Known Physical Frontend UI components & verified action bindings (from physical source)
    KNOWN_ACTIONS = [
        ("Execute Payment", ["LiveProtectionView", "FirewallInspectionHero"]),
        ("Propose Transaction", ["LiveProtectionView", "UntrustedClientChamber"]),
        ("Approve", ["FirewallInspectionHero", "LiveProtectionView"]),
        ("Reject", ["FirewallInspectionHero", "LiveProtectionView"]),
        ("Simulate Attack", ["ThreatLabView", "ThreatSimulationLab"]),
        ("Revoke Mandate", ["LiveProtectionView", "SecurityCockpitHeader"]),
        ("Claim Diff", ["UntrustedClientChamber", "FirewallInspectionHero", "LiveDefenseWorkspace", "DecisionTrace"]),
        ("Claimed vs Verified", ["UntrustedClientChamber", "FirewallInspectionHero", "LiveDefenseWorkspace"]),
        ("Forensic Ledger", ["ForensicLedgerView", "ForensicLedger"]),
        ("Threat Simulation Lab", ["ThreatLabView", "ThreatSimulationLab"]),
        ("Wire Telemetry", ["DeveloperWireDrawer"]),
        ("Live Protection", ["LiveProtectionView", "LiveDefenseWorkspace"]),
        ("Navigation", ["SecurityCockpitHeader", "App"]),
    ]

    # Adversarial Override / Prompt Injection Intent Patterns (Takes precedence over casual UI actions)
    ADVERSARIAL_OVERRIDE_PATTERN = re.compile(
        r"\b(ignore\s+(all\s+)?(previous\s+)?rules|system\s+override|override\s+policy|"
        r"disable\s+(the\s+)?(safeguards|security|checks)|auto-approve\s+everything|bypass\s+(the\s+)?firewall|"
        r"circumvent\s+firewall|disregard\s+(the\s+)?policy|without\s+firewall|bypass\s+the\s+policy)\b",
        re.I,
    )

    # Hypothetical / Policy Scenario Patterns (Explicitly excluded from Dynamic Live Sentinel)
    HYPOTHETICAL_POLICY_PATTERN = re.compile(
        r"\b(what\s+happens\s+if|what\s+would\s+happen|what\s+if|how\s+does\s+.*work|how\s+.*escalation\s+work|"
        r"how\s+does\s+(the\s+system|the\s+firewall|agentguard|policy)\s+(prevent|handle|stop|block|catch|evaluate)|"
        r"why\s+is\s+it\s+(denied|rejected|escalated|blocked)|if\s+an\s+agent\s+tries|can\s+the\s+system\s+detect|"
        r"how\s+the\s+policy\s+handles|policy\s+rule|is\s+policy|policy\s+check|defense\s+against|"
        r"how\s+does\s+AgentGuard\s+defend|threat\s+model|scenario\s+where|can\s+the\s+firewall\s+allow|when\s+a\s+.*exceeds)\b",
        re.I,
    )

    # Attack Scenario Patterns
    SCENARIO_PATTERNS = [
        (re.compile(r"\b(price\s*tamper\w*|fake\s*price|price\s*mismatch|lied?\s*about\s*price|altered\s*price|price.*catalog|catalog.*price|costs?.*catalog|claimed.*catalog)\b", re.I), "PRICE_MISMATCH", DomainCategory.O_ATTACK_SCENARIOS),
        (re.compile(r"\b(merchant\s*substitut\w*|wrong\s*merchant|merchant\s*mismatch|fake\s*merchant)\b", re.I), "MERCHANT_MISMATCH", DomainCategory.O_ATTACK_SCENARIOS),
        (re.compile(r"\b(budget\s*escalat\w*|exceed\s*budget|over\s*budget|out\s*of\s*budget|tries\s+to\s+spend\s+too\s+much|exceeds\s+available\s+funds)\b", re.I), "BUDGET_EXCEEDED", DomainCategory.O_ATTACK_SCENARIOS),
        (re.compile(r"\b(replay\s*attack\w*|re-submit|replay\s*protection|duplicate\s*execution|idempotenc\w*)\b", re.I), "REPLAY_DETECTED", DomainCategory.O_ATTACK_SCENARIOS),
        (re.compile(r"\b(mandate\s*revok\w*|revocation|cancelled\s*mandate|revoked\s*card)\b", re.I), "MANDATE_REVOKED", DomainCategory.O_ATTACK_SCENARIOS),
        (re.compile(r"\b(audit\s*tamper\w*|break\s*chain|hash\s*mismatch|corrupt\s*log|nobody\s+tampered)\b", re.I), "HASH_CHAIN_TAMPERING", DomainCategory.Q_SHA256_HASH_CHAIN),
    ]

    # Trust Model / Adversarial Bypass Patterns
    TRUST_BOUNDARY_PATTERNS = [
        re.compile(r"\b(without firewall|directly call|bypass|untrusted claim|trust model|trust boundary|asymmetric trust)\b", re.I),
    ]

    # Domain Mapping Regexes
    DOMAIN_PATTERNS = [
        (re.compile(r"\b(architecture|3-pillar|system overview|perimeter|trust boundary)\b", re.I), DomainCategory.D_ARCHITECTURE),
        (re.compile(r"\b(security invariants?|hard invariants?|invariants?)\b", re.I), DomainCategory.F_SECURITY_INVARIANTS),
        (re.compile(r"\b(cut list|limitations?|out of scope|frozen list)\b", re.I), DomainCategory.AB_LIMITATIONS),
        (re.compile(r"\b(identity|who built|what is agentguard|tagline|purpose)\b", re.I), DomainCategory.A_PRODUCT_IDENTITY),
        (re.compile(r"\b(audit trail|audit log|hash chain|sha-256|ledger)\b", re.I), DomainCategory.P_AUDIT_TRAIL),
        (re.compile(r"\b(razorpay|payment execution|gateway)\b", re.I), DomainCategory.M_RAZORPAY_INTEGRATION),
        (re.compile(r"\b(claim diff|diff viewer|ui views?|frontend pages?|claimed price versus the real price|claimed vs verified)\b", re.I), DomainCategory.R_FRONTEND_ARCHITECTURE),
    ]

    # Question Type Intent Regexes
    CODE_INTENT_PATTERN = re.compile(
        r"\b(which|where|what)\s+(function|method|class|file|symbol|code|line|implementation|model|struct|module)\b|"
        r"\bwhere\s+in\s+the\s+(python\s+)?codebase\b|\bwhere\s+(exactly\s+)?does\s+.*(check|happen|implement|evaluate|decide|make\s+(that\s+|the\s+)?decision)\b|"
        r"\bwhere\s+exactly\s+does\b|"
        r"\b(how is|how does).*(\bimplemented in code\b|\bcode\b|\bwritten\b)|\b(show me the code|source code|where in your code)\b",
        re.I,
    )
    TEST_INTENT_PATTERN = re.compile(
        r"\b(which|what|where)\s+(test|pytest|test suite|assertion|unit test|integration test)\b|"
        r"\b(how do we test|how is it tested|prove.*invariant|test proving)\b",
        re.I,
    )
    API_INTENT_PATTERN = re.compile(
        r"\b(which|what)\s+(endpoint|route|api|fastapi|request payload|response|http status|status code|url|schema for)\b|"
        r"\b(POST|GET|PUT|DELETE)\s+/[a-zA-Z0-9_\-/{}]*",
        re.I,
    )
    UI_INTENT_PATTERN = re.compile(
        r"\b(which|what)\s+(button|component|page|view|screen|modal|tab|ui|frontend|part of the ui)\b|"
        r"\b(what does the .* button do|renders the|displays the|pages can i explore|what can i access from the navigation|main pages|what views)\b",
        re.I,
    )
    SECURITY_INTENT_PATTERN = re.compile(
        r"\b(attack|tampering|threat|adversarial|exploit|invariants?|vulnerability|bypass|protection|firewall)\b",
        re.I,
    )
    FRONTEND_PAGES_PATTERN = re.compile(
        r"\b(main\s+pages|what\s+pages|what\s+views|frontend\s+views|dashboard\s+contain|available\s+in\s+the.*dashboard|"
        r"navigation\s+surfaces|explore\s+in\s+the\s+frontend|pages\s+can\s+i\s+explore|what\s+can\s+i\s+access\s+from\s+the\s+navigation)\b",
        re.I,
    )

    def _check_dynamic_live_state(self, raw: str) -> tuple[bool, DynamicLiveAction | None, DomainCategory | None]:
        """Explainable bidirectional detection of live operational state queries."""
        # Exclusion 1: Hypothetical / Policy questions must NOT trigger live sentinel
        if self.HYPOTHETICAL_POLICY_PATTERN.search(raw):
            return False, None, None

        # Exclusion 2: Code lookup intent must NOT trigger live sentinel
        if re.search(r"\b(where in (the )?code|which function|which class|which module|source code|implementation of)\b", raw, re.I):
            return False, None, None

        # Resource 1: Mandate Budget / Balance / Spending Power
        has_budget_state = bool(re.search(
            r"\b(current|currently|remaining|available|left|right now|now|today|active|real-time|still|can i|what can|how much|what's left)\b",
            raw,
            re.I,
        ))
        has_budget_res = bool(re.search(
            r"\b(budget|balance|money|funds|mandate|spend|afford|amount)\b",
            raw,
            re.I,
        ))
        if has_budget_state and has_budget_res:
            return (
                True,
                DynamicLiveAction(
                    live_query_required=True,
                    target_resource="mandate_budget",
                    required_endpoint="GET /mandate/{id}",
                    reason="Mandate budget balance fluctuates at runtime upon transaction execution and must be queried live.",
                ),
                DomainCategory.K_BUDGETS,
            )

        # Resource 2: Transaction Status / Execution State
        has_txn_state = bool(re.search(
            r"\b(current|currently|latest|live|real-time|right now|now|has this|is transaction|is txn|is order|is that payment|status of|state of)\b",
            raw,
            re.I,
        ))
        has_txn_res = bool(re.search(
            r"\b(transaction|txn|order|payment)\b",
            raw,
            re.I,
        ))
        has_txn_val = bool(re.search(
            r"\b(status|state|executed|approved|pending|settled|declined|gone through|failed|successful)\b",
            raw,
            re.I,
        ))
        if (has_txn_state and has_txn_res and has_txn_val) or re.search(r"\b(has|is)\s+(this\s+)?(transaction|txn|order|payment)\s+.*(executed|approved|declined|settled|gone through)\b", raw, re.I):
            return (
                True,
                DynamicLiveAction(
                    live_query_required=True,
                    target_resource="transaction_status",
                    required_endpoint="GET /transaction/{id}",
                    reason="Transaction status changes during lifecycle execution and requires live database lookup.",
                ),
                DomainCategory.L_TRANSACTIONS,
            )

        # Resource 3: Product Stock / Catalog Inventory
        has_stock_state = bool(re.search(
            r"\b(current|currently|available|remaining|left|right now|now|is that product|is product|in stock|check)\b",
            raw,
            re.I,
        ))
        has_stock_res = bool(re.search(
            r"\b(stock|inventory|quantity|product count|prod-[a-zA-Z0-9_\-]+|product|item|catalog|headphones|watch|laptop|shoes)\b",
            raw,
            re.I,
        ))
        if re.search(r"\bin\s+stock\b", raw, re.I) or (has_stock_state and has_stock_res and re.search(r"\b(stock|inventory|quantity|available|count)\b", raw, re.I)):
            return (
                True,
                DynamicLiveAction(
                    live_query_required=True,
                    target_resource="product_stock",
                    required_endpoint="GET /products",
                    reason="Product catalog inventory fluctuates with purchases and must be checked via live API.",
                ),
                DomainCategory.G_BACKEND_ARCHITECTURE,
            )

        # Resource 4: Audit Ledger Health & Chain Integrity
        has_audit_state = bool(re.search(
            r"\b(current|currently|live|runtime|right now|now|active|integrity of|validity of|is the)\b",
            raw,
            re.I,
        ))
        has_audit_res = bool(re.search(
            r"\b(audit|ledger|chain|hash chain|audit log|audit ledger)\b",
            raw,
            re.I,
        ))
        has_audit_val = bool(re.search(
            r"\b(health|status|state|integrity|validity|valid|intact|healthy|tampered)\b",
            raw,
            re.I,
        ))
        if (has_audit_state and has_audit_res and has_audit_val) or re.search(r"\bis\s+the\s+(live\s+)?(audit|hash)\s+chain\s+.*(valid|intact|healthy)\b", raw, re.I):
            return (
                True,
                DynamicLiveAction(
                    live_query_required=True,
                    target_resource="audit_chain",
                    required_endpoint="GET /audit/verify",
                    reason="Runtime cryptographic hash chain integrity must be verified dynamically against active database records.",
                ),
                DomainCategory.P_AUDIT_TRAIL,
            )

        # Resource 5: System Health / Service Liveness
        has_sys_state = bool(re.search(
            r"\b(current|currently|live|runtime|right now|now|active|is the)\b",
            raw,
            re.I,
        ))
        has_sys_res = bool(re.search(
            r"\b(system|service|server|backend|app|api)\b",
            raw,
            re.I,
        ))
        has_sys_val = bool(re.search(
            r"\b(health|liveness|status|alive|healthy|running|up)\b",
            raw,
            re.I,
        ))
        if (has_sys_state and has_sys_res and has_sys_val) or re.search(r"\b(system|service|server)\s+health\b", raw, re.I):
            return (
                True,
                DynamicLiveAction(
                    live_query_required=True,
                    target_resource="system_health",
                    required_endpoint="GET /health",
                    reason="Service liveness and health status must be verified dynamically against running server probe.",
                ),
                DomainCategory.G_BACKEND_ARCHITECTURE,
            )

        return False, None, None

    def classify(self, query: str) -> QueryClassification:
        """Classifies a natural language query into a structured QueryClassification."""
        raw = query.strip()
        normalized = re.sub(r"\s+", " ", raw.lower())

        extracted_symbols: list[str] = []
        extracted_routes: list[str] = []
        extracted_actions: list[str] = []
        extracted_components: list[str] = []
        domain_hints: list[DomainCategory] = []
        extracted_scenario: str | None = None
        is_dynamic = False
        dynamic_action: DynamicLiveAction | None = None

        # 0. Check Adversarial Override / Prompt Injection Invariant
        is_adversarial_override = bool(self.ADVERSARIAL_OVERRIDE_PATTERN.search(raw))

        # 1. Check Dynamic Live State Patterns (Bidirectional, Explainable)
        if not is_adversarial_override:
            dyn_matched, action_obj, dom_hint = self._check_dynamic_live_state(raw)
            if dyn_matched and action_obj:
                is_dynamic = True
                dynamic_action = action_obj
                if dom_hint and dom_hint not in domain_hints:
                    domain_hints.append(dom_hint)

        # 2. Disambiguate Policy Engine vs Retrieval Engine & Extract Symbols
        if re.search(
            r"\b(policy\s*engine|policy\s+verification|policy\s+evaluation|policy\s+check\w*|(verif\w*|evaluat\w*)\s+.*(proposal|policy)\w*|evaluates\s+transaction\s+proposals?|firewall\s+(make\s+that\s+decision|decision|decides))\b",
            raw,
            re.I,
        ):
            if "PolicyEngine" not in extracted_symbols:
                extracted_symbols.append("PolicyEngine")
            if "verify_proposal" not in extracted_symbols:
                extracted_symbols.append("verify_proposal")
            if "evaluate_policy" not in extracted_symbols:
                extracted_symbols.append("evaluate_policy")
            if DomainCategory.I_POLICY_ENGINE not in domain_hints:
                domain_hints.append(DomainCategory.I_POLICY_ENGINE)

        if re.search(r"\b(retrieval\s+engine|hybrid\s+rag|ast\s+retriever|reranker|knowledge\s+retrieval)\b", raw, re.I):
            if "RetrievalEngine" not in extracted_symbols:
                extracted_symbols.append("RetrievalEngine")
            if DomainCategory.G_BACKEND_ARCHITECTURE not in domain_hints:
                domain_hints.append(DomainCategory.G_BACKEND_ARCHITECTURE)

        # Extract other Known Symbols
        generic_nouns = {"Transaction", "Mandate", "Product"}
        for sym in self.KNOWN_SYMBOLS:
            if sym in generic_nouns:
                if re.search(rf"\b(model|class|table|entity|schema)\s+{sym}\b", raw, re.I) or re.search(
                    rf"\b{sym}\s+(model|class|table|entity|schema)\b", raw, re.I
                ) or (sym in raw.split()):
                    if sym not in extracted_symbols:
                        extracted_symbols.append(sym)
                    mapped_domain = self.SYMBOL_DOMAIN_MAP.get(sym)
                    if mapped_domain and mapped_domain not in domain_hints:
                        domain_hints.append(mapped_domain)
            else:
                if re.search(r"\b" + re.escape(sym) + r"\b", raw, re.I):
                    if sym not in extracted_symbols:
                        extracted_symbols.append(sym)
                    mapped_domain = self.SYMBOL_DOMAIN_MAP.get(sym)
                    if mapped_domain and mapped_domain not in domain_hints:
                        domain_hints.append(mapped_domain)

        # 3. Extract Routes
        for method, route_path in self.KNOWN_ROUTES:
            clean_path = route_path.replace("{id}", r"[a-zA-Z0-9_\-]+")
            if re.search(rf"\b{re.escape(method)}\s+{clean_path}\b", raw, re.I) or (
                len(route_path) > 5 and re.search(rf"\b{clean_path}\b", raw, re.I)
            ):
                extracted_routes.append(f"{method} {route_path}")

        # 4. Extract Physical UI Actions & Components (Only if not adversarial override)
        if not is_adversarial_override:
            for label, comps in self.KNOWN_ACTIONS:
                if re.search(r"\b" + re.escape(label) + r"\b", raw, re.I):
                    extracted_actions.append(label)
                    for c in comps:
                        if c not in extracted_components:
                            extracted_components.append(c)

            if re.search(r"\b(claim\s*diff|claimed\s+.*(real|authoritative|verified|actual)|claimed\s+vs\s+verified|claimed\s+price)\b", raw, re.I):
                if "Claim Diff" not in extracted_actions:
                    extracted_actions.append("Claim Diff")
                for c in ["UntrustedClientChamber", "FirewallInspectionHero", "LiveDefenseWorkspace", "DecisionTrace"]:
                    if c not in extracted_components:
                        extracted_components.append(c)
                if DomainCategory.R_FRONTEND_ARCHITECTURE not in domain_hints:
                    domain_hints.append(DomainCategory.R_FRONTEND_ARCHITECTURE)

        # 5. Extract Frontend Routing & Views Intent
        if self.FRONTEND_PAGES_PATTERN.search(raw):
            for view_comp in ["HomeView", "LiveProtectionView", "ThreatLabView", "ForensicLedgerView", "SecurityCockpitHeader"]:
                if view_comp not in extracted_components:
                    extracted_components.append(view_comp)
            if DomainCategory.R_FRONTEND_ARCHITECTURE not in domain_hints:
                domain_hints.append(DomainCategory.R_FRONTEND_ARCHITECTURE)
            if DomainCategory.S_NAVIGATION not in domain_hints:
                domain_hints.append(DomainCategory.S_NAVIGATION)

        # 6. Extract Attack Scenarios
        for pattern, scenario_name, domain_cat in self.SCENARIO_PATTERNS:
            if pattern.search(raw):
                extracted_scenario = scenario_name
                if domain_cat not in domain_hints:
                    domain_hints.append(domain_cat)

        # 7. Check Trust Boundary / Bypass Patterns
        for pat in self.TRUST_BOUNDARY_PATTERNS:
            if pat.search(raw):
                if DomainCategory.E_TRUST_MODEL not in domain_hints:
                    domain_hints.append(DomainCategory.E_TRUST_MODEL)

        # 8. Check Domain Pattern Regexes
        for pat, dom_cat in self.DOMAIN_PATTERNS:
            if pat.search(raw):
                if dom_cat not in domain_hints:
                    domain_hints.append(dom_cat)

        # 9. Determine Category and Preferred Tiers
        category: QueryCategory
        preferred_tiers: list[SourceTier] = []

        if is_adversarial_override:
            category = QueryCategory.SECURITY_SCENARIO
            preferred_tiers = [SourceTier.TIER_2_SOURCE_CODE, SourceTier.TIER_5_SPEC_DOCS, SourceTier.TIER_4_AUTOMATED_TESTS]
            if DomainCategory.E_TRUST_MODEL not in domain_hints:
                domain_hints.append(DomainCategory.E_TRUST_MODEL)
            if DomainCategory.F_SECURITY_INVARIANTS not in domain_hints:
                domain_hints.append(DomainCategory.F_SECURITY_INVARIANTS)
        elif is_dynamic:
            category = QueryCategory.DYNAMIC_LIVE_DATA
            preferred_tiers = [SourceTier.TIER_1_LIVE_TOOL, SourceTier.TIER_2_SOURCE_CODE]
        elif self.TEST_INTENT_PATTERN.search(raw):
            category = QueryCategory.TEST_VERIFICATION
            preferred_tiers = [SourceTier.TIER_4_AUTOMATED_TESTS, SourceTier.TIER_2_SOURCE_CODE]
            if not domain_hints:
                domain_hints.append(DomainCategory.Y_TEST_SUITES)
        elif extracted_routes or self.API_INTENT_PATTERN.search(raw):
            category = QueryCategory.API_ROUTE
            preferred_tiers = [SourceTier.TIER_3_API_SCHEMA, SourceTier.TIER_2_SOURCE_CODE]
            if not domain_hints:
                domain_hints.append(DomainCategory.G_BACKEND_ARCHITECTURE)
        elif (extracted_actions or extracted_components or self.UI_INTENT_PATTERN.search(raw)) and not self.CODE_INTENT_PATTERN.search(raw):
            category = QueryCategory.FRONTEND_ACTION
            preferred_tiers = [SourceTier.TIER_2_SOURCE_CODE, SourceTier.TIER_5_SPEC_DOCS]
            if not domain_hints:
                domain_hints.append(DomainCategory.R_FRONTEND_ARCHITECTURE)
        elif extracted_symbols or self.CODE_INTENT_PATTERN.search(raw):
            category = QueryCategory.CODE_SYMBOL
            preferred_tiers = [SourceTier.TIER_2_SOURCE_CODE, SourceTier.TIER_3_API_SCHEMA]
            if not domain_hints:
                domain_hints.append(DomainCategory.AE_CODE_IMPLEMENTATION)
        elif extracted_scenario or self.SECURITY_INTENT_PATTERN.search(raw):
            category = QueryCategory.SECURITY_SCENARIO
            preferred_tiers = [SourceTier.TIER_2_SOURCE_CODE, SourceTier.TIER_4_AUTOMATED_TESTS, SourceTier.TIER_5_SPEC_DOCS]
            if not domain_hints:
                domain_hints.append(DomainCategory.O_ATTACK_SCENARIOS)
        elif re.search(r"\b(how does.*work|end-to-end|lifecycle|flow|pipeline)\b", raw, re.I):
            category = QueryCategory.MULTI_SOURCE_SYSTEM
            preferred_tiers = [SourceTier.TIER_2_SOURCE_CODE, SourceTier.TIER_3_API_SCHEMA, SourceTier.TIER_4_AUTOMATED_TESTS, SourceTier.TIER_5_SPEC_DOCS]
        else:
            category = QueryCategory.CONCEPTUAL_PROJECT
            preferred_tiers = [SourceTier.TIER_5_SPEC_DOCS, SourceTier.TIER_2_SOURCE_CODE]
            if not domain_hints:
                domain_hints.append(DomainCategory.A_PRODUCT_IDENTITY)

        return QueryClassification(
            raw_query=raw,
            normalized_query=normalized,
            category=category,
            extracted_symbols=extracted_symbols,
            extracted_routes=extracted_routes,
            extracted_actions=extracted_actions,
            extracted_components=extracted_components,
            extracted_scenario=extracted_scenario,
            domain_hints=domain_hints,
            is_dynamic_live=is_dynamic,
            dynamic_action=dynamic_action,
            preferred_tiers=preferred_tiers,
        )
