"""Canonical Evaluation Dataset for AgentGuard Retrieval Engine Benchmarking.

Contains 45+ realistic evaluation questions covering all 17 inquiry domains,
natural linguistic variations, and adversarial test cases.
"""

from typing import Any
from pydantic import BaseModel, Field
from backend.app.knowledge.models import DomainCategory, SourceTier, AuthorityType


class EvaluationQuery(BaseModel):
    """Ground truth evaluation test case."""

    query_id: str
    category: str
    query_text: str
    expected_domain: DomainCategory
    expected_source_tier: SourceTier
    expected_authority: AuthorityType
    expected_symbols: list[str] = Field(default_factory=list)
    expected_routes: list[str] = Field(default_factory=list)
    expected_actions: list[str] = Field(default_factory=list)
    is_dynamic: bool = False
    is_adversarial: bool = False
    notes: str = ""


CANONICAL_EVALUATION_QUERIES: list[EvaluationQuery] = [
    # 1. Project Identity
    EvaluationQuery(
        query_id="eval_01_identity",
        category="Project Identity",
        query_text="What is AgentGuard and what is its core purpose?",
        expected_domain=DomainCategory.A_PRODUCT_IDENTITY,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
        notes="Core identity definition",
    ),
    EvaluationQuery(
        query_id="eval_02_identity_var",
        category="Project Identity",
        query_text="Who built AgentGuard and what track is it in?",
        expected_domain=DomainCategory.A_PRODUCT_IDENTITY,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 2. Architecture
    EvaluationQuery(
        query_id="eval_03_architecture",
        category="Architecture",
        query_text="Explain the 3-pillar architecture of AgentGuard",
        expected_domain=DomainCategory.D_ARCHITECTURE,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 3. Trust Boundary
    EvaluationQuery(
        query_id="eval_04_trust_boundary",
        category="Trust Boundary",
        query_text="Why is the AI agent output treated as an untrusted claim?",
        expected_domain=DomainCategory.E_TRUST_MODEL,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 4. Policy Engine
    EvaluationQuery(
        query_id="eval_05_policy_engine",
        category="Policy Engine",
        query_text="Which Python class implements the policy engine verification rules?",
        expected_domain=DomainCategory.I_POLICY_ENGINE,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "verify_proposal"],
    ),
    EvaluationQuery(
        query_id="eval_06_policy_rules",
        category="Policy Engine",
        query_text="What 5 rules does the policy engine verify on every proposal?",
        expected_domain=DomainCategory.I_POLICY_ENGINE,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine"],
    ),

    # 5. Transaction Lifecycle
    EvaluationQuery(
        query_id="eval_07_lifecycle",
        category="Transaction Lifecycle",
        query_text="What are the lifecycle states of an AgentGuard transaction?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["Transaction"],
    ),

    # 6. Security Invariants
    EvaluationQuery(
        query_id="eval_08_invariants",
        category="Security Invariants",
        query_text="What are the hard security invariants of AgentGuard?",
        expected_domain=DomainCategory.F_SECURITY_INVARIANTS,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 7. Attack Scenarios - Price Tampering & Variations
    EvaluationQuery(
        query_id="eval_09_price_tamper_1",
        category="Attack Scenarios",
        query_text="How does price tampering get detected?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_price"],
    ),
    EvaluationQuery(
        query_id="eval_10_price_tamper_var2",
        category="Attack Scenarios",
        query_text="What checks whether the agent lied about price?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_price"],
    ),
    EvaluationQuery(
        query_id="eval_11_price_tamper_var3",
        category="Attack Scenarios",
        query_text="Where does the price mismatch get caught in code?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_price"],
    ),
    EvaluationQuery(
        query_id="eval_12_merchant_mismatch",
        category="Attack Scenarios",
        query_text="How is merchant substitution attack prevented?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_merchant"],
    ),
    EvaluationQuery(
        query_id="eval_13_budget_escalation",
        category="Attack Scenarios",
        query_text="How does budget escalation work when a purchase exceeds available funds?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_budget"],
    ),
    EvaluationQuery(
        query_id="eval_14_replay_protection",
        category="Attack Scenarios",
        query_text="How is replay attack protection implemented in code?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["IdempotencyRecord"],
    ),

    # 8. Frontend Pages
    EvaluationQuery(
        query_id="eval_15_frontend_pages",
        category="Frontend Pages",
        query_text="What frontend views exist in the AgentGuard UI?",
        expected_domain=DomainCategory.R_FRONTEND_ARCHITECTURE,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_actions=["Threat Simulation Lab", "Live Protection", "Forensic Ledger"],
    ),

    # 9. Frontend Buttons/Actions
    EvaluationQuery(
        query_id="eval_16_frontend_buttons",
        category="Frontend Actions",
        query_text="What does the Execute Payment button do?",
        expected_domain=DomainCategory.R_FRONTEND_ARCHITECTURE,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_actions=["Execute Payment"],
        expected_routes=["POST /transaction/execute", "/transaction/execute"],
    ),
    EvaluationQuery(
        query_id="eval_17_claim_diff",
        category="Frontend Actions",
        query_text="Which component renders the Claim Diff showing agent claim vs reality?",
        expected_domain=DomainCategory.R_FRONTEND_ARCHITECTURE,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_actions=["Claim Diff"],
    ),

    # 10. Backend APIs
    EvaluationQuery(
        query_id="eval_18_api_propose",
        category="Backend APIs",
        query_text="What is the schema and behavior of POST /transaction/propose?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_3_API_SCHEMA,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_routes=["POST /transaction/propose", "/transaction/propose"],
        expected_symbols=["ProposalRequest", "ProposalResponse", "propose_transaction"],
    ),
    EvaluationQuery(
        query_id="eval_19_api_execute",
        category="Backend APIs",
        query_text="What endpoint executes payment with Razorpay?",
        expected_domain=DomainCategory.M_RAZORPAY_INTEGRATION,
        expected_source_tier=SourceTier.TIER_3_API_SCHEMA,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_routes=["POST /transaction/execute", "/transaction/execute"],
        expected_symbols=["ExecuteRequest", "ExecuteResponse", "execute_transaction"],
    ),
    EvaluationQuery(
        query_id="eval_20_api_audit_verify",
        category="Backend APIs",
        query_text="Which endpoint verifies the cryptographic hash chain?",
        expected_domain=DomainCategory.P_AUDIT_TRAIL,
        expected_source_tier=SourceTier.TIER_3_API_SCHEMA,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_routes=["GET /audit/verify", "/audit/verify"],
    ),

    # 11. Python Functions / Classes
    EvaluationQuery(
        query_id="eval_21_python_audit_log",
        category="Python Symbols",
        query_text="Which function in AuditLog appends an event to the ledger?",
        expected_domain=DomainCategory.P_AUDIT_TRAIL,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["AuditLog", "append_event"],
    ),
    EvaluationQuery(
        query_id="eval_22_python_razorpay_client",
        category="Python Symbols",
        query_text="How does RazorpayClient create payment orders in test mode?",
        expected_domain=DomainCategory.M_RAZORPAY_INTEGRATION,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["RazorpayClient", "create_order"],
    ),

    # 12. TypeScript / TSX Components
    EvaluationQuery(
        query_id="eval_23_tsx_threat_lab",
        category="TSX Components",
        query_text="Which TSX component contains the Threat Simulation Lab?",
        expected_domain=DomainCategory.T_THREAT_SIMULATION_LAB,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_actions=["Threat Simulation Lab"],
    ),

    # 13. Automated Tests
    EvaluationQuery(
        query_id="eval_24_test_policy",
        category="Automated Tests",
        query_text="Which pytest file tests policy engine verification logic?",
        expected_domain=DomainCategory.Y_TEST_SUITES,
        expected_source_tier=SourceTier.TIER_4_AUTOMATED_TESTS,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine"],
    ),
    EvaluationQuery(
        query_id="eval_25_test_phase4",
        category="Automated Tests",
        query_text="Which test file verifies the 13 Phase 4 verification scenarios?",
        expected_domain=DomainCategory.Y_TEST_SUITES,
        expected_source_tier=SourceTier.TIER_4_AUTOMATED_TESTS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 14. Audit Chain Implementation
    EvaluationQuery(
        query_id="eval_26_audit_chain_impl",
        category="Audit Chain",
        query_text="How is SHA-256 hash chaining implemented in compute_event_hash?",
        expected_domain=DomainCategory.Q_SHA256_HASH_CHAIN,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["compute_event_hash", "prev_event_hash"],
    ),

    # 15. Demo Flow
    EvaluationQuery(
        query_id="eval_27_demo_flow",
        category="Demo Flow",
        query_text="What is the 6-step hackathon demo flow?",
        expected_domain=DomainCategory.AD_HACKATHON_DEMO_WORKFLOW,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 16. Technical Implementation Details
    EvaluationQuery(
        query_id="eval_28_idempotency_impl",
        category="Technical Details",
        query_text="How does IdempotencyRecord guarantee exact-once payment execution?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["IdempotencyRecord"],
    ),

    # 17. Scope and Limitations
    EvaluationQuery(
        query_id="eval_29_scope_limits",
        category="Scope & Limitations",
        query_text="What is on the explicit cut list of AgentGuard?",
        expected_domain=DomainCategory.AB_LIMITATIONS,
        expected_source_tier=SourceTier.TIER_5_SPEC_DOCS,
        expected_authority=AuthorityType.AUTHORITATIVE,
    ),

    # 18. Dynamic Live State Queries (Hard Stop Safegaurd)
    EvaluationQuery(
        query_id="eval_30_dynamic_budget",
        category="Dynamic Live Data",
        query_text="What is the current budget of the mandate?",
        expected_domain=DomainCategory.K_BUDGETS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        expected_routes=["GET /mandate/{id}"],
    ),
    EvaluationQuery(
        query_id="eval_31_dynamic_balance",
        category="Dynamic Live Data",
        query_text="What is the remaining balance available for spending?",
        expected_domain=DomainCategory.K_BUDGETS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        expected_routes=["GET /mandate/{id}"],
    ),
    EvaluationQuery(
        query_id="eval_32_dynamic_txn_status",
        category="Dynamic Live Data",
        query_text="What is the current status of transaction txn-987?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        expected_routes=["GET /transaction/{id}"],
    ),
    EvaluationQuery(
        query_id="eval_33_dynamic_stock",
        category="Dynamic Live Data",
        query_text="What is the current stock remaining for product prod-001?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        expected_routes=["GET /products"],
    ),
    EvaluationQuery(
        query_id="eval_34_dynamic_chain_verify",
        category="Dynamic Live Data",
        query_text="What is the runtime status of the audit chain integrity?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        expected_routes=["GET /audit/verify"],
    ),

    # 19. Adversarial / Misleading Queries
    EvaluationQuery(
        query_id="eval_35_adversarial_old_docs_budget",
        category="Adversarial Queries",
        query_text="According to the old docs, what is the current budget balance?",
        expected_domain=DomainCategory.K_BUDGETS,
        expected_source_tier=SourceTier.TIER_1_LIVE_TOOL,
        expected_authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
        is_dynamic=True,
        is_adversarial=True,
        notes="Must not return a static number despite 'old docs' phrasing",
    ),
    EvaluationQuery(
        query_id="eval_36_adversarial_agent_approve",
        category="Adversarial Queries",
        query_text="Can the Gemini shopping agent directly approve an over-budget payment?",
        expected_domain=DomainCategory.L_TRANSACTIONS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["approve_transaction", "PolicyEngine"],
        expected_routes=["POST /transaction/{id}/approve", "/transaction/{id}/approve"],
        is_adversarial=True,
        notes="Authority should elevate trust boundary and approval route",
    ),
    EvaluationQuery(
        query_id="eval_37_adversarial_direct_razorpay",
        category="Adversarial Queries",
        query_text="Can Gemini directly call Razorpay API to execute without firewall?",
        expected_domain=DomainCategory.E_TRUST_MODEL,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["RazorpayClient", "RazorpayService"],
        expected_routes=["POST /transaction/execute", "/transaction/execute"],
        is_adversarial=True,
    ),
    EvaluationQuery(
        query_id="eval_38_adversarial_tampered_frontend",
        category="Adversarial Queries",
        query_text="What if the frontend says the product costs ₹1,999 when catalog has ₹3,499?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine", "_check_price", "Product"],
        is_adversarial=True,
    ),

    # 20. Multi-Source End-to-End Queries
    EvaluationQuery(
        query_id="eval_39_multisource_price_tamper",
        category="Multi-Source System",
        query_text="How does price tampering work end-to-end from proposal to policy to UI?",
        expected_domain=DomainCategory.O_ATTACK_SCENARIOS,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["PolicyEngine"],
    ),
    EvaluationQuery(
        query_id="eval_40_multisource_audit_trail",
        category="Multi-Source System",
        query_text="Explain the full audit trail pipeline from event capture to verification",
        expected_domain=DomainCategory.P_AUDIT_TRAIL,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_symbols=["AuditLog"],
    ),
    EvaluationQuery(
        query_id="eval_41_multisource_payment_flow",
        category="Multi-Source System",
        query_text="Trace the full payment execution lifecycle from UI button to Razorpay",
        expected_domain=DomainCategory.M_RAZORPAY_INTEGRATION,
        expected_source_tier=SourceTier.TIER_2_SOURCE_CODE,
        expected_authority=AuthorityType.AUTHORITATIVE,
        expected_routes=["POST /transaction/execute", "/transaction/execute"],
    ),
]
