# CONVENTIONS.md — Repo Structure & Coding Standards

## 1. Repo structure

```
/
├── PRD.md
├── TRD.md
├── ARCHITECTURE.md
├── AGENTS.md
├── THREAT_MODEL.md
├── CONVENTIONS.md
├── TEST_PLAN.md
├── SEED_DATA.md
├── README.md                      # written last, for judges/graders
├── .env.example                   # every required var, no real secrets
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── api/
│   │   │   ├── routes_transaction.py   # /transaction/propose, /transaction/execute
│   │   │   └── routes_mandate.py       # mandate create/revoke
│   │   ├── policy/
│   │   │   ├── engine.py               # pure policy engine, no I/O
│   │   │   └── reason_codes.py
│   │   ├── models/                     # SQLAlchemy models, one file per entity
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── migrations/             # Alembic
│   │   ├── integrations/
│   │   │   ├── razorpay_client.py      # test-mode wrapper
│   │   │   └── gemini_client.py        # reference agent's LLM calls only
│   │   ├── audit/
│   │   │   └── audit_log.py            # hash-chained event writer
│   │   └── config.py                   # loads from env, no hardcoded secrets
│   ├── tests/
│   │   ├── unit/                       # policy engine, no HTTP
│   │   └── integration/                # real endpoint + adversarial payloads
│   └── requirements.txt
│
├── frontend/
│   ├── app/ (or src/)
│   │   ├── components/
│   │   │   ├── ShoppingAgentChat/
│   │   │   ├── DecisionTrace/
│   │   │   ├── AttackConsole/
│   │   │   └── AuditHistory/
│   │   └── lib/api.ts                  # typed client matching TRD.md exactly
│   └── package.json
│
└── scripts/
    └── seed_db.py                      # loads SEED_DATA.md values into Postgres
```

## 2. API response conventions

Every endpoint returns a consistent envelope. Success and error responses both follow this shape — don't invent a different shape per endpoint.

```json
{
  "success": true,
  "data": { "...": "..." },
  "error": null
}
```

On failure:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PRICE_MISMATCH",
    "message": "Claimed price does not match authoritative catalog price."
  }
}
```

`error.code` values are exactly the reason codes listed in TRD.md §4 — do not invent new ones ad hoc; if a new case is genuinely needed, add it to TRD.md first, then implement it.

## 3. HTTP status mapping (keep consistent across all endpoints)
- `200` — request processed, decision may still be DENY/ESCALATE (the *call* succeeded even if the *transaction* was denied — this distinction matters for the demo)
- `400` — malformed request (missing/invalid fields)
- `403` — used specifically for policy DENY on `/transaction/execute` (matches the ChatGPT review's suggested convention: `403 { "decision": "DENY", "reason": "..." }`)
- `404` — transaction/mandate not found
- `409` — replay/already-executed conflict
- `500` — genuine server error (should be rare; log to audit trail regardless)

## 4. Naming conventions
- Python: `snake_case` for functions/variables, `PascalCase` for classes/Pydantic models
- Reason codes: `SCREAMING_SNAKE_CASE`, exactly as listed in TRD.md §4 — never abbreviate or reword them ad hoc
- DB tables: plural, `snake_case` (matches TRD.md schema exactly)
- Frontend components: `PascalCase` folders, one component per folder

## 5. Environment variables (`.env.example` — fill in real values in untracked `.env`)
```
DATABASE_URL=postgresql://user:pass@localhost:5432/firewall_db
GEMINI_API_KEY=
RAZORPAY_TEST_KEY_ID=
RAZORPAY_TEST_KEY_SECRET=
TRANSACTION_EXPIRY_SECONDS=300
PRICE_MISMATCH_TOLERANCE=0.01
```

Never commit `.env`. Never let the Gemini agent's context include real key values.

## 6. Logging & audit conventions
- Application logs (stdout/file) are for debugging — normal dev logging, nothing special
- Audit events (the hash-chained table in TRD.md) are a **separate, distinct concern** — every policy decision, every state transition, every Razorpay call gets one, written server-side only, never derived from a log line after the fact

## 7. Git conventions
- Commit messages: short imperative summary, e.g. `feat: add price-mismatch detection to policy engine`
- When something breaks and gets fixed, say so in the commit message or a `NOTES.md` entry (per AGENTS.md §8) — this becomes pitch material
- One phase (from AGENTS.md build order) roughly maps to one PR/branch if working with branches, or a clearly separated batch of commits if working directly on main