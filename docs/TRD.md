# TRD — Agentic Commerce Firewall

## 1. Tech Stack
- **Language:** Python (majority of the system — API, policy engine, agents)
- **API framework:** FastAPI
- **LLM:** Gemini API (`google-genai` Python SDK) — used only by the reference shopping agent to interpret user requests and propose transactions; the LLM has no authorization power
- **Database:** PostgreSQL — chosen deliberately for real ACID transactional guarantees, row-level locking, and atomic budget reservation under concurrency (a NoSQL/eventually-consistent store would undermine the "server-authoritative, no double-spend" security property)
- **Payments:** Razorpay **test-mode** API (sandbox keys) — same request/response shape as production, no real money moves
- **Frontend:** React/Next.js — chat UI + Decision Trace panel + Attack Console (see UI_ARCHITECTURE section of ARCHITECTURE.md)
- **Explicitly not used:** vector DB, LangGraph, multi-agent frameworks, blockchain, custom crypto

## 2. Database Schema

```
users
  id (uuid, pk)
  name
  email
  created_at

merchants
  id (uuid, pk)
  name
  category
  status (active | suspended)

products
  id (uuid, pk)
  merchant_id (fk -> merchants.id)
  name
  price (decimal, authoritative — this is the only price that matters)
  currency
  stock
  active (bool)

mandates
  id (uuid, pk)
  user_id (fk -> users.id)
  budget_total (decimal)
  budget_remaining (decimal)
  merchant_scope (nullable — restrict to specific merchant(s) if set)
  category_scope (nullable)
  max_transaction_amount (decimal)
  status (active | revoked | expired)
  created_at
  expires_at

transactions
  id (uuid, pk)                      -- server-generated, never client-supplied
  mandate_id (fk -> mandates.id)
  user_id (fk -> users.id)
  merchant_id (fk -> merchants.id)   -- server-derived, not trusted from agent
  product_id (fk -> products.id)
  claimed_price (decimal)            -- what the AI/agent said (untrusted, stored for audit/comparison only)
  authoritative_price (decimal)      -- server-derived from products.price at propose time
  quantity (int)
  authoritative_total (decimal)      -- server-computed, never trusted from client
  status (proposed | allowed | escalated | approved | rejected | executing | success | failed | denied | expired | revoked)
  reason_code (see section 4)
  nonce (server-generated)
  idempotency_key
  created_at
  expires_at                         -- propose→execute window, e.g. 5 minutes
  executed_at

approvals
  id (uuid, pk)
  transaction_id (fk -> transactions.id)
  status (pending | approved | rejected)
  approver_id
  created_at
  resolved_at

idempotency_records
  idempotency_key (pk)
  transaction_id (fk -> transactions.id)
  response_snapshot (jsonb)          -- so a retried execute call returns the exact same response, never re-executes
  created_at

audit_events
  id (uuid, pk)
  transaction_id (fk -> transactions.id, nullable for mandate-level events)
  event_type (e.g. PROPOSED, VERIFIED, POLICY_DECISION, ESCALATED, APPROVED, EXECUTED, DENIED, REPLAY_ATTEMPT)
  actor (agent | firewall | human | razorpay)
  payload_hash                       -- hash of the event payload
  prev_hash                          -- hash of the previous event in the chain (hash-chained audit log)
  created_at
```

## 3. API Contracts

### `POST /transaction/propose`

**Request**
```json
{
  "user_id": "uuid",
  "mandate_id": "uuid",
  "agent_claim": {
    "merchant_id": "uuid",
    "product_id": "uuid",
    "claimed_price": 1999.00,
    "quantity": 1
  }
}
```

**Server logic (in this order):**
1. Load mandate → must exist, `status == active`, not past `expires_at` → else `MANDATE_EXPIRED` / `MANDATE_REVOKED`
2. Load product/merchant from DB by ID → this is the authoritative source, `claimed_price` is never used for math, only for comparison
3. Compare `claimed_price` vs authoritative `products.price` → if divergence beyond tolerance → `PRICE_MISMATCH` → decision `DENY`
4. Check merchant/category scope on the mandate → if violated → `MERCHANT_MISMATCH` → `DENY`
5. Compute `authoritative_total = authoritative_price * quantity` server-side
6. Compare `authoritative_total` against `mandate.max_transaction_amount` and `mandate.budget_remaining`:
   - within both → decision `ALLOW`
   - exceeds either but is a legitimate proposal → decision `ESCALATE`
7. Generate `transaction_id`, `nonce`, `expires_at` server-side
8. Persist transaction row, write `audit_events` entry

**Response**
```json
{
  "transaction_id": "uuid",
  "decision": "ALLOW | ESCALATE | DENY",
  "reason_code": "ALLOW | PRICE_MISMATCH | MERCHANT_MISMATCH | BUDGET_EXCEEDED | MANDATE_EXPIRED | MANDATE_REVOKED",
  "authoritative_total": 3499.00,
  "expires_at": "iso8601"
}
```

### `POST /transaction/execute`

**Request**
```json
{
  "transaction_id": "uuid",
  "idempotency_key": "string"
}
```

**Server logic (in this order):**
1. If `idempotency_key` already seen → return the stored `response_snapshot` immediately, do nothing else (idempotent replay-safe retry)
2. Load transaction by `transaction_id` → must exist
3. Re-validate everything from scratch, do not trust the propose-step decision as final:
   - mandate still `active`, not revoked/expired since propose time → else `MANDATE_REVOKED` / `MANDATE_EXPIRED`
   - transaction not past its own `expires_at` → else `TRANSACTION_EXPIRED`
   - transaction `status` is `allowed` or `approved` (not already `success`, which would be a replay) → else `ALREADY_EXECUTED` / `REPLAY_DETECTED`
   - if `status == escalated` and no matching `approvals` row with `status == approved` → return `ESCALATION_REQUIRED`, do not execute
   - re-derive authoritative price fresh from `products` table again (protects against price having changed between propose and execute)
4. Atomically reserve/decrement `mandate.budget_remaining` (DB transaction + row lock — must be a real atomic operation, not a read-then-write race)
5. Call Razorpay test-mode API to create/capture the payment
6. On success → `status = success`, budget decrement finalized, `audit_events` entry, store `response_snapshot` under `idempotency_key`
7. On failure → `status = failed`, release the reserved budget, allow retry via the same `idempotency_key`/`transaction_id` (never creates a second charge)

**Response**
```json
{
  "transaction_id": "uuid",
  "status": "success | failed | escalation_required | denied",
  "reason_code": "...",
  "razorpay_payment_id": "string | null"
}
```

## 4. Reason Codes (canonical list)
`ALLOW`, `PRICE_MISMATCH`, `MERCHANT_MISMATCH`, `QUANTITY_INVALID`, `BUDGET_EXCEEDED`, `MANDATE_EXPIRED`, `MANDATE_REVOKED`, `TRANSACTION_EXPIRED`, `REPLAY_DETECTED`, `ALREADY_EXECUTED`, `ESCALATION_REQUIRED`, `APPROVED_BY_HUMAN`, `REJECTED_BY_HUMAN`, `PAYMENT_DECLINED`

## 5. Transaction State Machine

```
PROPOSED
  ├─ (policy: within limits)      → ALLOWED
  ├─ (policy: over limits)        → ESCALATED
  └─ (policy: invalid)            → DENIED  [terminal]

ALLOWED
  ├─ execute() success            → EXECUTING → SUCCESS  [terminal]
  ├─ execute() payment declines   → EXECUTING → FAILED → (retry via same id) → EXECUTING → SUCCESS/FAILED
  ├─ mandate revoked before exec  → REVOKED   [terminal]
  └─ expires_at passed            → EXPIRED   [terminal]

ESCALATED
  ├─ approval: approved           → ALLOWED (then proceeds as above)
  └─ approval: rejected           → DENIED   [terminal]

SUCCESS
  └─ any further execute() attempt on this id → DENIED, reason REPLAY_DETECTED
```

## 6. Testing Requirements
- **Unit tests** on the policy engine in isolation — all six scenarios + hidden seventh, pure logic, no HTTP
- **Integration/security tests** — hit the actual running `/transaction/propose` and `/transaction/execute` endpoints with adversarial payloads, assert on real HTTP status codes and response bodies. This is the layer that actually proves the security claims; unit tests alone are not sufficient.
- Explicit adversarial cases to cover: over-budget, expired mandate, revoked mandate, price mismatch, quantity manipulation, merchant substitution, replay, transaction-limit abuse, stale/expired proposal, concurrent overspending (two simultaneous executes racing against the same budget), LLM lying about price.