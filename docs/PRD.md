# PRD — Agentic Commerce Firewall

## 1. Context
Built for the Razorpay AI Buildathon, track: **AI Growth & Agentic Commerce**. Submission requires a public GitHub repo, a 5-minute pitch video, and architecture documentation, by 5 September.

## 2. Problem
Autonomous AI agents (shopping assistants, procurement bots, personal agents) are starting to make purchase decisions and initiate payments on a user's behalf. The AI making the decision is not trustworthy by construction — it can hallucinate a price, misidentify a merchant, or be manipulated by adversarial input. Today there is no standard authorization boundary that sits between "an AI agent proposes a transaction" and "money actually moves."

## 3. Product
**Agentic Commerce Firewall** — a deterministic authorization boundary that sits between any autonomous AI agent and financial execution on Razorpay.

**We are explicitly not building a shopping agent as the product.** The shopping agent included in this project is a reference client / demonstration attack surface. The product is the firewall itself — the propose → verify → policy → execute boundary that would sit in front of *any* agent, not just ours.

## 4. Core Positioning (use this language in the pitch)
> "We built a reference authorization layer that demonstrates how an autonomous shopping agent can be bounded before it reaches payment execution."

Not: "We solved autonomous commerce security" (too broad, indefensible).

## 5. Core Principle
**The LLM's output is an untrusted claim with zero authorization weight.** Nothing the model says about price, merchant, or quantity is trusted. Everything is independently re-derived from authoritative, server-side sources before a transaction is allowed to proceed.

> "The model is allowed to be wrong. It's not allowed to be authoritative."

## 6. Users / Actors
- **End user** — grants a mandate (budget + scope) to their AI agent
- **AI agent** — proposes transactions on the user's behalf (untrusted)
- **Firewall** — verifies, applies policy, decides ALLOW / ESCALATE / DENY
- **Human approver** — resolves escalations
- **Razorpay (test-mode)** — executes the actual payment once authorized

## 7. Functional Requirements

### 7.1 Mandate management
- A user can create a mandate: budget total, merchant/category scope, max single-transaction amount, expiry
- A user can revoke an active mandate at any time
- An expired or revoked mandate cannot authorize any transaction, including ones already in flight

### 7.2 Transaction proposal
- An agent proposes a transaction (merchant, product, claimed price, quantity) against a mandate
- The firewall independently looks up the authoritative price/merchant from its own catalog — the agent's claimed price is never trusted for authorization
- If claimed vs. authoritative values diverge beyond tolerance → DENY (`PRICE_MISMATCH`)
- If within budget and scope → ALLOW
- If it exceeds budget/limits but is otherwise valid → ESCALATE for human approval

### 7.3 Transaction execution
- Execution independently re-validates everything (mandate still active, transaction not expired, not already executed, budget still available) — it does not trust the propose step's decision as final
- Idempotent: retrying the same transaction (e.g. after a payment failure) never double-charges
- A previously executed transaction cannot be re-executed (`REPLAY_DETECTED`)
- Payment is executed via Razorpay **test-mode** APIs only — no real money moves

### 7.4 The six required demo scenarios (frozen, must all work end-to-end)
1. Happy path — within budget → ALLOW → success
2. Over-budget → ESCALATE → human approval
3. Price tampering (claimed ≠ authoritative) → DENY
4. Replay of a completed transaction ID → DENY
5. Payment failure → safe retry, no duplicate charge
6. Mandate revoked mid-session → DENY

Plus the emergent 7th: the live "LLM lies" decision trace (claimed vs. authoritative side-by-side) — this is not a separate feature, it falls out of scenario 3's implementation.

### 7.5 Observability
- Every decision (ALLOW/ESCALATE/DENY) and every tool/API call is recorded in a server-side, hash-chained audit log
- A user/judge can reconstruct the full reasoning trace of any transaction after the fact

## 8. Explicitly Out of Scope
No vector DB, no LangGraph, no multi-agent architecture, no blockchain, no custom cryptography, no arbitrary risk scoring, no merchant SaaS dashboard, no real-money transactions, no real bank/card credentials. JWT (if used at all) is an implementation detail, never the architecture.

## 9. Success Criteria
- All six scenarios + the hidden seventh work end-to-end, demonstrated live through the UI, backed by real HTTP-level integration/security tests (not just unit tests)
- Deployed and live, not just runnable from a clone
- A judge unfamiliar with the project can watch a 5-minute demo and understand: what the firewall does, why the LLM is untrusted, and see it defeat an attack live

## 10. Non-Goals
This is not a general-purpose payments platform, not a production merchant dashboard, and not a claim to have "solved" agentic commerce security broadly — it's a reference implementation of one boundary pattern.