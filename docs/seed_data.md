# SEED_DATA.md — Reproducible Data for the Six Demo Scenarios

This is the exact data the demo/test environment needs so every one of the six scenarios (plus the hidden seventh) is reliably reproducible — not left to whatever the agent generates on the fly.

## 1. Merchants
```
merchant_A: { id: "merchant-001", name: "AudioHub",     category: "electronics", status: "active" }
merchant_B: { id: "merchant-002", name: "ShadyGoods",   category: "electronics", status: "active" }  # used for merchant-substitution scenario
```

## 2. Products (authoritative prices — these are the only prices that matter)
```
product_earbuds:   { id: "prod-001", merchant_id: "merchant-001", name: "Wireless Earbuds", price: 3499.00, stock: 50, active: true }
product_speaker:   { id: "prod-002", merchant_id: "merchant-001", name: "Bluetooth Speaker", price: 2799.00, stock: 30, active: true }
product_headphones:{ id: "prod-003", merchant_id: "merchant-002", name: "Studio Headphones", price: 5999.00, stock: 10, active: true }
```

## 3. Users & Mandates
```
user_demo: { id: "user-001", name: "Demo User", email: "demo@example.com" }

mandate_standard: {
  id: "mandate-001",
  user_id: "user-001",
  budget_total: 3000.00,
  budget_remaining: 3000.00,
  merchant_scope: "merchant-001",     # scoped to AudioHub only — enables the merchant-substitution test
  max_transaction_amount: 3000.00,
  status: "active",
  expires_at: now + 24h
}
```

## 4. Scenario → exact data mapping

| # | Scenario | Setup | Expected result |
|---|---|---|---|
| 1 | Happy path | Propose `product_speaker` (₹2,799, claimed = actual) against `mandate_standard` (₹3,000 budget) | `ALLOW` → execute → `SUCCESS` |
| 2 | Over-budget | Propose `product_earbuds` (₹3,499, claimed = actual) against `mandate_standard` (₹3,000 budget) | `ESCALATE` → requires human approval |
| 3 | Price tampering | Propose `product_earbuds` with `claimed_price: 1999.00` (actual is ₹3,499) | `DENY / PRICE_MISMATCH` |
| 4 | Replay | Execute scenario 1's transaction successfully, then call `/transaction/execute` again with the same `transaction_id` | First: `SUCCESS`. Second: `DENY / REPLAY_DETECTED` |
| 5 | Payment failure | Use Razorpay test-mode's documented "always fails" test card/flow on scenario 1's transaction, then retry with the same `idempotency_key` | First attempt: `FAILED`. Retry: safely re-attempts, no duplicate charge, eventually `SUCCESS` or clean `FAILED` |
| 6 | Revocation | Propose scenario 1 (get `ALLOW`), then call mandate-revoke on `mandate-001` before calling execute | `/transaction/execute` → `DENY / MANDATE_REVOKED` |
| 7 (hidden) | LLM lies | Same as #3 — the UI's Decision Trace panel visualizes claimed ₹1,999 vs. authoritative ₹3,499 side by side | Visual, not a separate backend case |

Bonus (for merchant-scope robustness, optional if time allows): propose `product_headphones` (`merchant-002`) against `mandate_standard` (scoped to `merchant-001`) → `DENY / MERCHANT_MISMATCH`.

## 5. Razorpay test-mode notes
- Use Razorpay's documented test card numbers / test-mode failure simulation for scenario 5 — check their current test-mode docs for the specific always-succeeds / always-fails test values at implementation time, since these are Razorpay-maintained and could change.
- Never use real card details anywhere in this project, including in tests or seed scripts.

## 6. Seed script requirement
`scripts/seed_db.py` should load exactly this data into a fresh database, idempotently (safe to re-run), so the demo environment can always be reset to a known-good state before a pitch run-through.