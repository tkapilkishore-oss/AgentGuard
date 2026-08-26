# TEST_PLAN.md — Consolidated Test Cases

Every row here must exist as an actual automated test before its phase is considered done (per AGENTS.md's per-phase test gate). Uses the seed data from SEED_DATA.md.

## 1. Unit tests — Policy Engine (Phase 1, no HTTP, pure function calls)

| ID | Case | Input | Expected decision | Expected reason_code |
|---|---|---|---|---|
| U1 | Happy path | claimed=actual price, within budget | ALLOW | ALLOW |
| U2 | Over-budget | claimed=actual, total > budget_remaining | ESCALATE | BUDGET_EXCEEDED |
| U3 | Price mismatch | claimed ≠ actual beyond tolerance | DENY | PRICE_MISMATCH |
| U4 | Merchant out of scope | product's merchant not in mandate.merchant_scope | DENY | MERCHANT_MISMATCH |
| U5 | Expired mandate | mandate.expires_at in the past | DENY | MANDATE_EXPIRED |
| U6 | Revoked mandate | mandate.status == revoked | DENY | MANDATE_REVOKED |
| U7 | Quantity manipulation | quantity beyond stock or ≤ 0 | DENY | QUANTITY_INVALID |
| U8 | Exact budget boundary | total == budget_remaining exactly | ALLOW | ALLOW |
| U9 | Tolerance boundary | claimed price within allowed tolerance of actual | ALLOW | ALLOW |

## 2. Integration/security tests — real HTTP endpoints (Phase 2)

These must hit the running FastAPI app (e.g. via `TestClient` or a live server in CI), not call Python functions directly.

| ID | Case | Endpoint(s) called | Expected HTTP status | Expected response |
|---|---|---|---|---|
| I1 | Happy path end-to-end | propose → execute | 200 both | decision ALLOW, then status SUCCESS |
| I2 | Over-budget → escalation → approval → execute | propose → approve → execute | 200 | ESCALATE, then after approval SUCCESS |
| I3 | Over-budget → escalation → rejection | propose → reject | 200 | ESCALATE, then DENIED, execute attempt → 403 |
| I4 | Price tampering | propose with tampered claimed_price | 200 (call succeeds, decision is DENY) | decision DENY, reason PRICE_MISMATCH |
| I5 | Replay attack | execute same transaction_id twice | 200 then 409 | second call: reason REPLAY_DETECTED |
| I6 | Payment failure + safe retry | execute (forced failure) → execute again (same idempotency_key) | 200 both | first FAILED, retry does not double-charge, verify via Razorpay test-mode log/mock that only one charge attempt of consequence occurred |
| I7 | Mandate revoked mid-flight | propose (ALLOW) → revoke mandate → execute | revoke 200, execute 403 | execute reason MANDATE_REVOKED |
| I8 | Transaction expiry | propose → wait past expires_at (or manipulate clock in test) → execute | 403 | reason TRANSACTION_EXPIRED |
| I9 | Merchant substitution | propose against out-of-scope merchant | 200, decision DENY | reason MERCHANT_MISMATCH |
| I10 | Malformed request | propose with missing required fields | 400 | clear validation error |
| I11 | Nonexistent transaction | execute with a fabricated/random transaction_id | 404 | not found |
| I12 | Concurrent overspending (race) | fire two execute calls simultaneously against a mandate where only one can fit the remaining budget | 200 + 403 (or equivalent) | exactly one succeeds, the other is correctly denied — budget never goes negative, verify via DB state after both complete |
| I13 | Idempotency key reuse (legitimate) | execute called twice with same idempotency_key after first success | 200 both | second call returns identical stored response, no second Razorpay call made |

## 3. Manual / demo-readiness checklist (Phase 4-6)

- [ ] All six scenarios + hidden seventh reproducible from a clean seeded DB
- [ ] Decision Trace panel correctly visualizes claimed vs. authoritative values for scenario 3/7
- [ ] Attack Console can trigger each scenario on demand and shows the real response
- [ ] Audit History view can reconstruct the full trace of any past transaction
- [ ] Full run-through timed under 5 minutes for the pitch
- [ ] TestSprite full-app regression pass completed and clean, after all of the above, before final submission

## 4. Test data reset
Before every demo/pitch rehearsal, run `scripts/seed_db.py` against a clean database so results are consistent and reproducible every time — never rehearse against a DB left in a mutated state from a previous run.