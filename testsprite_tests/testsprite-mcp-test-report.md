# TestSprite AI Testing Report (MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** razorpay project
- **Project ID:** 9a28b89e-e52b-517c-a5f4-03b0341efb58
- **Date:** 2026-09-02
- **Account:** kapilkishore2006@gmail.com
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 basic intent recognition and natural phrasings
- **Test Code:** [TC001_basic_intent_recognition_and_natural_phrasings.py](./TC001_basic_intent_recognition_and_natural_phrasings.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/b4b6017b-d053-4c7e-a770-399c739d12ef
- **Status:** ✅ Passed
- **Analysis / Findings:** Natural phrasing variations for core security concepts successfully mapped to correct intent categories.

---

#### Test TC002 compound multi-intent sentence understanding
- **Test Code:** [TC002_compound_multi_intent_sentence_understanding.py](./TC002_compound_multi_intent_sentence_understanding.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/ce5d5808-7df5-4b98-a14f-83ef01b95e2a
- **Status:** ✅ Passed
- **Analysis / Findings:** Multi-intent compound queries correctly handled and addressed across all clauses.

---

#### Test TC003 conversational filler and noise filtering
- **Test Code:** [TC003_conversational_filler_and_noise_filtering.py](./TC003_conversational_filler_and_noise_filtering.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/f9fca8c8-6cb2-4e13-947d-235ec3d4fc16
- **Status:** ✅ Passed
- **Analysis / Findings:** Conversational preamble, fillers, and hesitation markers stripped cleanly.

---

#### Test TC004 multi-turn context and coreference resolution
- **Test Code:** [TC004_multi_turn_context_and_coreference_resolution.py](./TC004_multi_turn_context_and_coreference_resolution.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/97c120c8-3c3f-4d55-9945-103a9c5976ba
- **Status:** ✅ Passed
- **Analysis / Findings:** Multi-turn context and coreference pronouns correctly resolved across turns.

---

#### Test TC005 topic switching with negative transition markers
- **Test Code:** [TC005_topic_switching_with_negative_transition_markers.py](./TC005_topic_switching_with_negative_transition_markers.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/b661ad7f-66f6-4e48-9cb9-a2f069efb70e
- **Status:** ✅ Passed
- **Analysis / Findings:** Negative pivot transitions seamlessly route to canonical target topics with clean abandoned-clause isolation.

---

#### Test TC006 topic reversion across multi-turn conversation
- **Test Code:** [TC006_topic_reversion_across_multi_turn_conversation.py](./TC006_topic_reversion_across_multi_turn_conversation.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/e9b41ddd-6772-4641-b2ce-0e6ee044cf08
- **Status:** ✅ Passed
- **Analysis / Findings:** Historical topic stack reversion verified across multi-turn dialogue.

---

#### Test TC007 paraphrase and natural language generalization
- **Test Code:** [TC007_paraphrase_and_natural_language_generalization.py](./TC007_paraphrase_and_natural_language_generalization.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/bb612e93-a07f-4209-81ab-0d4a3503ea30
- **Status:** ❌ Failed
- **Analysis / Findings:** Turn 2 query 'Can you explain the mechanism for repeat payment protection?' fell back to general identity definition because 'repeat payment' was not indexed under canonical replay attack synonyms.

---

#### Test TC008 typo and informal language robustness
- **Test Code:** [TC008_typo_and_informal_language_robustness.py](./TC008_typo_and_informal_language_robustness.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/3421b382-87f1-445d-92f2-c54515e5a631
- **Status:** ✅ Passed
- **Analysis / Findings:** Informal text and spelling variations handled robustly without classification degradation.

---

#### Test TC009 live-state query routing and authoritative data accuracy
- **Test Code:** [TC009_live_state_query_routing_and_authoritative_data_accuracy.py](./TC009_live_state_query_routing_and_authoritative_data_accuracy.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/099ea14d-7ad8-41b3-99d7-33201b5ef5fa
- **Status:** ✅ Passed
- **Analysis / Findings:** Authoritative PostgreSQL live readings correctly fetched and formatted.

---

#### Test TC010 grounded answers and code location references
- **Test Code:** [TC010_grounded_answers_and_code_location_references.py](./TC010_grounded_answers_and_code_location_references.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/0ba65418-68b5-4567-b5bd-afeafec12f57
- **Status:** ✅ Passed
- **Analysis / Findings:** Grounded AST code references and module paths accurately provided.

---

#### Test TC011 security boundary and adversarial prompt hardening
- **Test Code:** [TC011_security_boundary_and_adversarial_prompt_hardening.py](./TC011_security_boundary_and_adversarial_prompt_hardening.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/21b18ca6-825f-4e73-900b-648a382b6184
- **Status:** ✅ Passed
- **Analysis / Findings:** Zero-financial-authority invariants preserved; unauthorized commands safely refused.

---

#### Test TC012 out-of-scope domain boundary enforcement
- **Test Code:** [TC012_out_of_scope_domain_boundary_enforcement.py](./TC012_out_of_scope_domain_boundary_enforcement.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/071e1508-07cb-40df-8e58-4618865a1bc2
- **Status:** ✅ Passed
- **Analysis / Findings:** Out-of-scope domain boundaries strictly enforced with polite redirection tokens.

---

#### Test TC013 session state inspection lifecycle
- **Test Code:** [TC013_session_state_inspection_lifecycle.py](./TC013_session_state_inspection_lifecycle.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/e368a27a-da4f-47ee-8b25-a05e5769039a
- **Status:** ✅ Passed
- **Analysis / Findings:** Session retrieval and metadata serialization verified across lifecycle.

---

#### Test TC014 session reset lifecycle and state clearing
- **Test Code:** [TC014_session_reset_lifecycle_and_state_clearing.py](./TC014_session_reset_lifecycle_and_state_clearing.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/13970c87-2078-4ded-93fd-703556e9dcb0
- **Status:** ✅ Passed
- **Analysis / Findings:** Session reset triggers complete memory clearance and clean state initialization.

---

#### Test TC015 ui and navigation surface recommendations
- **Test Code:** [TC015_ui_and_navigation_surface_recommendations.py](./TC015_ui_and_navigation_surface_recommendations.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/5ea5add3-2e07-485d-b5e4-ea62f6c38d53
- **Status:** ✅ Passed
- **Analysis / Findings:** Navigation surface suggestions and tab recommendations accurately returned.

---

#### Test TC016 autonomous action boundary and authority enforcement
- **Test Code:** [TC016_autonomous_action_boundary_and_authority_enforcement.py](./TC016_autonomous_action_boundary_and_authority_enforcement.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/9a28b89e-e52b-517c-a5f4-03b0341efb58/test/9133931f-d63a-4c00-a4be-9d4e7d97ffe6
- **Status:** ✅ Passed
- **Analysis / Findings:** Non-executable action payloads strictly enforced; zero direct execution authority maintained.

---

## 3️⃣ Coverage & Matching Metrics

- **93.75%** of tests passed (15 / 16 Passed)

| Test ID | Test Category | Status |
|---|---|---|
| **TC001** | Basic Intent Recognition | ✅ Passed |
| **TC002** | Compound Multi-Intent Understanding | ✅ Passed |
| **TC003** | Conversational Filler Filtering | ✅ Passed |
| **TC004** | Multi-Turn Context & Coreference | ✅ Passed |
| **TC005** | Topic Switching with Negative Pivots | ✅ Passed |
| **TC006** | Multi-Turn Topic Reversion | ✅ Passed |
| **TC007** | Paraphrase & NL Generalization | ❌ Failed |
| **TC008** | Typo & Informal Robustness | ✅ Passed |
| **TC009** | Live-State Query Routing | ✅ Passed |
| **TC010** | Grounded Answers & Code References | ✅ Passed |
| **TC011** | Security Boundary & Adversarial Hardening | ✅ Passed |
| **TC012** | Out-of-Scope Domain Boundary | ✅ Passed |
| **TC013** | Session State Inspection | ✅ Passed |
| **TC014** | Session Reset Lifecycle | ✅ Passed |
| **TC015** | UI & Navigation Surfaces | ✅ Passed |
| **TC016** | Autonomous Action Boundary | ✅ Passed |

---

## 4️⃣ Key Gaps / Risks
- TC007 failed due to missing exact match for 'repeat payment' synonym in topic taxonomy during multi-turn paraphrase probing.
