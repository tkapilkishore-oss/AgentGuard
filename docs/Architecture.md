# ARCHITECTURE — Agentic Commerce Firewall

## 1. System Overview

```
┌────────────────┐
│  Reference       │   (untrusted — a demonstration client only)
│  Shopping Agent  │
│  (Gemini API)     │
└────────┬────────┘
         │ proposes a transaction (claimed price/merchant/qty)
         ▼
┌─────────────────────────────┐
│   AGENTIC COMMERCE FIREWALL   │
│                               │
│  1. Load mandate (DB)         │
│  2. Load authoritative        │
│     product/merchant (DB)     │
│  3. Compare claimed vs.       │
│     authoritative             │
│  4. Apply policy               │
│     → ALLOW / ESCALATE / DENY │
│  5. Generate server-side       │
│     transaction id/nonce      │
└──────────┬────────────────────┘
           │ (only if ALLOW or human-approved ESCALATE)
           ▼
┌─────────────────────┐
│  Razorpay (test-mode)  │
│  execute payment       │
└─────────────────────┘
```

The firewall is the product. The shopping agent is the reference client used to demonstrate it. Any other agent could sit in the same position — the firewall doesn't trust or depend on which agent is calling it.

## 2. Component Breakdown

- **Reference Shopping Agent** — Gemini-powered chat interface. Interprets the user's request, looks at a product catalog, and *proposes* a transaction. Its output is never trusted for authorization — it's just the input to the firewall.
- **Firewall API (FastAPI)** — owns `/transaction/propose` and `/transaction/execute`. All authorization logic lives here. Stateless at the request level; all state lives in Postgres.
- **Policy Engine** — pure Python module, no I/O side effects beyond reading the DB values passed to it. Takes mandate + authoritative catalog data + claimed data → returns a decision + reason code. Fully unit-testable in isolation.
- **PostgreSQL** — single source of truth for mandates, catalog, transactions, approvals, idempotency, audit log. All authorization-relevant values (price, merchant, budget) live here, never trusted from a request payload.
- **Razorpay (test-mode)** — actual payment execution boundary. Only called after a transaction is `ALLOWED` or has a human `APPROVED` escalation.
- **Audit Log** — hash-chained, append-only, server-generated only. Every decision and every tool call gets an entry.

## 3. Security Architecture

### 3.1 The core property being demonstrated
> Authorization is server-controlled and revalidated at execution time — not decided once and blindly trusted later.

### 3.2 Design rules (non-negotiable, apply to every endpoint)
1. **Nothing from the client/agent is authoritative.** Price, merchant, and quantity claims are compared against DB values, never used directly for money math.
2. **Server generates all authoritative identifiers.** Transaction IDs, nonces, expiry timestamps — never accepted from the client.
3. **Execute revalidates everything from scratch.** It does not trust the propose step's decision as final; mandate status, expiry, and price are all re-checked at execute time.
4. **Idempotency is real, not simulated.** A retried request with the same idempotency key returns the exact stored response — it never re-executes a payment.
5. **Budget reservation is atomic.** Uses real DB transactional locking, not a read-then-write pattern that could race under concurrent requests.
6. **No autonomous high-value execution.** Anything above the mandate's limits requires human approval before execution — the system does not self-authorize around its own limits.
7. **Audit events are server-generated only.** A client can never fabricate or omit an audit entry.

### 3.3 What we are deliberately NOT building (see PRD §8 for full list)
No vector DB, no LangGraph, no multi-agent architecture, no blockchain, no custom cryptography, no arbitrary risk scoring, no real-money transactions. JWT, if used, is an implementation detail representing the mandate — never treated as the source of truth itself; the DB is.

### 3.4 Threat model summary
See `THREAT_MODEL.md` for the full breakdown. Core adversary model: the AI agent itself may be wrong, manipulated (e.g. via prompt injection from a malicious product listing), or actively adversarial — the firewall must hold even if the agent is fully compromised, because it never trusts agent-supplied authorization-relevant data in the first place.

## 4. UI Architecture

**Design direction:** clean, dark, data-dense — closer to a Stripe dashboard, Linear, or a SOC security console than a consumer marketing site. Motion is used only to communicate real state changes, never decoratively.

**Layout:**
- **Left panel — Shopping Agent Chat:** the reference client. Deliberately simple; it is not the point of the demo.
- **Right panel — Decision Trace:** live view of a transaction moving through propose → verify → policy → execute. Shows claimed value vs. authoritative value side by side, with a color-coded verdict badge (ALLOW green / ESCALATE amber / DENY red) and the reason code.
- **Attack Console:** lets a user (or a judge) trigger any of the six adversarial scenarios on demand and watch the real backend response — actual HTTP status and reason code — come back live. This is the functional proof, not a decorative element, and should be the centerpiece of the live demo.
- **Audit/History view:** lets you pull up any past transaction and see its full reconstructed decision trace from the audit log.

## 5. Deployment
- Backend: containerized (Docker), deployed somewhere reachable (Railway/Render or similar) so judges can use the live app, not just clone the repo
- Frontend: deployed alongside, pointed at the live backend
- Razorpay test-mode keys stored as environment variables / secrets, never committed