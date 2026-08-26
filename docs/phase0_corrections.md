# PHASE0_CORRECTIONS.md — Resolved Contract Ambiguities

Apply these as amendments to TRD.md, ARCHITECTURE.md, THREAT_MODEL.md, TEST_PLAN.md, and CONVENTIONS.md. These are clarifications and small contract additions only — no architecture, scope, or track changes. Once merged, Phase 0 is frozen and coding begins.

---

## 1. Idempotency vs. Replay — exact semantics

**Rule:** the client generates a **new `idempotency_key` for every distinct attempt** to execute a transaction (standard practice — same as Stripe). `transaction_id` stays constant across retries of the same logical purchase; `idempotency_key` changes per attempt.

**Lookup order in `/transaction/execute`:**
1. If this exact `idempotency_key` has been seen before → return the stored `response_snapshot` for it immediately (safe retry of the *exact same call*, whether it previously succeeded or failed). Do not call Razorpay again.
2. Otherwise, load the transaction by `transaction_id`:
   - `status == SUCCESS` → this is a **new** idempotency key attempting to re-execute an already-completed transaction → `409 REPLAY_DETECTED`
   - `status == FAILED` (payment previously declined) → this is a **legitimate retry** → proceed to re-validate and re-attempt against Razorpay, store the new response under this new `idempotency_key`
   - `status == ALLOWED` or `status == APPROVED` → first execution attempt → proceed normally
   - `status == ESCALATED` with no approval yet → `202 ESCALATION_REQUIRED`
   - `status` in `DENIED / EXPIRED / REVOKED` → return that terminal state, `403`

This resolves the tension: reusing the same key is always safe (idempotent no-op), while a fresh key against an already-succeeded transaction is correctly caught as replay, and a fresh key against a failed one is correctly allowed to retry.

## 2. Human Approval Endpoints (new — add to TRD.md API contracts)

```
POST /transaction/{transaction_id}/approve
POST /transaction/{transaction_id}/reject
```

- Only valid when `transaction.status == ESCALATED`. Any other status → `400`.
- On approve: creates an `approvals` row (`status = approved`), transaction moves to `status = ALLOWED`, eligible for execute.
- On reject: creates an `approvals` row (`status = rejected`), transaction moves to `status = DENIED` (terminal), reason `REJECTED_BY_HUMAN`.
- These endpoints only ever operate on transactions already in `ESCALATED` — see rule 3 below for which reasons are even allowed to reach that state.

## 3. Approvable vs. Terminal — the critical security fix

**Only one condition may ever result in `ESCALATED`: exceeding `budget_remaining` or `max_transaction_amount` while everything else about the proposal is valid.**

Every other violation is a **terminal `DENY`**, decided at propose time, and can never be converted into an approvable state — no human approval endpoint can override it. Approval can only ever raise a budget ceiling for an otherwise-legitimate transaction; it can never fix a transaction that's invalid for any other reason.

| Reason | Reachable state |
|---|---|
| `BUDGET_EXCEEDED` (over budget or per-txn max, otherwise valid) | `ESCALATED` → approvable |
| `PRICE_MISMATCH` | `DENIED`, terminal |
| `MANDATE_REVOKED` | `DENIED`, terminal |
| `MANDATE_EXPIRED` | `DENIED`, terminal |
| `MERCHANT_MISMATCH` | `DENIED`, terminal |
| `QUANTITY_INVALID` | `DENIED`, terminal |
| `TRANSACTION_EXPIRED` | `DENIED`, terminal (execute-time only) |

Add this table to TRD.md §4 as the authoritative reference. This is what prevents "the AI can't bypass the limit, but the approval button can" from being possible even in principle.

## 4. Price Change Between Propose and Execute

**No new reason code.** Reuses `PRICE_MISMATCH`.

**Rule:** at execute time, the server re-derives the *current* authoritative price from `products` and compares it against the `authoritative_price` that was captured and stored on the transaction at propose time. If they differ beyond tolerance → `403 PRICE_MISMATCH`, transaction moves to `DENIED` (terminal). The agent must re-propose to get a fresh, current price.

This is semantically identical to the original price-mismatch case (server-derived truth diverging from what a transaction was authorized against) — no new concept needed.

## 5. Quantity Semantics (formalize in TRD.md)

- `quantity` must be a positive integer
- `quantity >= 1`
- `quantity <= products.stock`
- `quantity <= 10` (sane demo upper bound — prevents pathological requests; document as configurable via env if desired)
- `authoritative_total` is **always** `authoritative_price × quantity`, computed server-side. The agent's request must never include a `total` field at all — if it does, the server ignores it entirely (do not even accept it as a comparison field, to remove any temptation to accidentally trust it).
- Violating any of the above → `403 QUANTITY_INVALID`, terminal.

## 6. Merchant Substitution — remove the attack surface entirely

**Change the `/transaction/propose` request schema: remove `merchant_id` from `agent_claim`.**

The agent should never be asked to claim a merchant at all — it's fully derivable:
```
merchant = products[product_id].merchant_id
```

**Updated request body:**
```json
{
  "user_id": "uuid",
  "mandate_id": "uuid",
  "agent_claim": {
    "product_id": "uuid",
    "claimed_price": 1999.00,
    "quantity": 1
  }
}
```

Merchant scope validation then always operates on the server-derived merchant, never on anything the client could have claimed — closing the substitution vector by construction rather than by a runtime check alone. Update TRD.md's request schema and SEED_DATA.md's scenario descriptions accordingly (the merchant-substitution test now works by requesting a `product_id` that legitimately belongs to an out-of-scope merchant, not by lying about the merchant field).

## 7. HTTP Status Codes — frozen per endpoint

**`POST /transaction/propose`** → always `200` on a well-formed request; the business `decision` (`ALLOW`/`ESCALATE`/`DENY`) lives in the response body, not the status code. `400` only for malformed requests.

**`POST /transaction/execute`**
- `200` — `SUCCESS` or `FAILED` (a completed payment attempt, whether Razorpay approved or declined it — this is a business outcome, not a policy denial)
- `202` — `ESCALATION_REQUIRED` (valid but pending human action)
- `403` — policy/authorization denial (`PRICE_MISMATCH`, `MANDATE_REVOKED`, `MANDATE_EXPIRED`, `MERCHANT_MISMATCH`, `QUANTITY_INVALID`, `TRANSACTION_EXPIRED`, `REJECTED_BY_HUMAN`)
- `409` — `REPLAY_DETECTED`
- `404` — transaction not found
- `400` — malformed request

**`POST /transaction/{id}/approve` and `/reject`** → `200` on success, `400` if transaction isn't in `ESCALATED` state, `404` if not found.

Update CONVENTIONS.md §3 to this exact table, replacing the earlier looser version.

## 8. Concurrency Test (I12) — precise setup

Update TEST_PLAN.md's I12 to this exact scenario:

```
mandate.budget_remaining = ₹3,000

Transaction A: propose ₹2,000 → ALLOWED (transaction_id = TA)
Transaction B: propose ₹2,000 → ALLOWED (transaction_id = TB)

Fire execute(TA) and execute(TB) concurrently.

Expected:
- Exactly one of {A, B} → SUCCESS
- The other → 403, BUDGET_EXCEEDED (re-checked at execute time, budget no longer sufficient)
- Final mandate.budget_remaining == ₹1,000 (never negative, never double-spent)
```

This must be two genuinely distinct transactions (different `transaction_id`s) — testing this with one transaction executed twice would test replay/idempotency instead of atomic concurrent budget reservation.

---

## Freeze statement

Once these 8 points are merged into the relevant docs: no unresolved contract-level ambiguities remain. Architecture, scope, demo scenarios, tech stack, API semantics, state machine, database invariants, reason codes, approval semantics, idempotency semantics, and test expectations are frozen. Coding starts at Phase 1 (policy engine + unit tests).