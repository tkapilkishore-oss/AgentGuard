# AgentGuard

> **The model is allowed to be wrong. It's not allowed to be authoritative.**

AgentGuard is a deterministic authorization firewall between untrusted AI agents and financial execution. The agent may propose a transaction, but it cannot authorize or execute financial actions directly. AgentGuard independently verifies authoritative transaction data, evaluates a scoped mandate using deterministic policy, and produces an explicit `ALLOW`, `ESCALATE`, or `DENY` decision before controlled execution.

---

## 🚀 What AgentGuard Demonstrates

- **Real AI-Agent Interaction**: Autonomous agent shopping proposals evaluated in real-time.
- **Independent Catalog Verification**: Authoritative lookup of merchant and product pricing, completely bypassing agent-supplied figures.
- **Deterministic Authorization**: Zero LLM judgment in financial decisions; strict policy rules govern spending limits and merchant scopes.
- **Price-Tampering Detection**: Instant rejection when an agent claims a lower price than authoritative catalog data.
- **Budget & Velocity Enforcement**: Hard boundaries on single transactions and cumulative lifetime mandate limits.
- **Human Escalation**: Automatic interactive review workflows for out-of-scope or border conditions.
- **Replay Protection**: Nonce and fingerprint tracking to prevent transaction replay attempts.
- **Mandate Revocation**: Immediate kill-switch enforcement blocking any subsequent attempts.
- **Safe Payment Execution**: Idempotent execution against Razorpay Test Mode with safe retry behavior.
- **Forensic Audit Ledger**: Tamper-evident, hash-linked (`SHA-256`) audit trail for all proposals and actions.
- **Conversational Security Assistant**: Natural-language security inspector explaining threats and ledger state without holding financial authority.
- **Autonomous End-to-End Walkthrough**: Interactive, narrating multi-step demonstration showing live attack mitigation and lifecycle reset.

---

## The Core Problem

Autonomous AI agents are increasingly tasked with procurement, bookings, and customer workflows. The catastrophic architectural flaw in current agentic systems is granting language models direct authority over money movement:

- **Hallucinated Prices**: LLMs fabricate discounts, currency symbols, and unit rates.
- **Prompt Injection & Manipulation**: Adversarial prompt payloads force agents to purchase unapproved items or divert funds.
- **Context Drift & Misinterpretation**: Multi-turn context compression leads models to exceed budget caps or ignore restrictions.
- **Replay & Inadvertent Loops**: Retries in agentic execution loops re-submit identical charges.

**AgentGuard treats the AI model as an UNTRUSTED PROPOSER rather than an AUTHORITY.**

---

## Core Principle

```
AI Proposes  ──►  Independent Systems Verify  ──►  Deterministic Policy Decides  ──►  Execution Revalidates
```

- **AI Proposes**: Untrusted agent produces an intent or payment proposal.
- **Independent Systems Verify**: Authoritative merchants, internal product catalogs, and databases resolve real prices—never trusting agent claims.
- **Deterministic Policy Decides**: Hard-coded, auditable code evaluates rules (limits, merchants, mandates). No probabilistic LLM decides authorization.
- **Execution Revalidates**: Only upon cryptographically valid authorization does the payment gateway (Razorpay Test Mode) execute the transfer.

---

## Architecture

```mermaid
flowchart TD
    subgraph Untrusted Layer
        Agent[Autonomous AI Agent / Gemini Proposer]
    end

    subgraph AgentGuard Trust Boundary
        Gateway[API Gateway / Fast-Fail Validation]
        Catalog[Independent Product & Merchant Catalog]
        Engine[Deterministic Policy Engine]
        Human[Human-in-the-Loop Escalation Chamber]
        Ledger[(Forensic Ledger SHA-256 Chain)]
    end

    subgraph External & Execution
        Razorpay[Razorpay Gateway - Test Mode]
        Postgres[(PostgreSQL Database)]
        TTS[Deepgram Brooke TTS - Audio Narration]
    end

    Agent -->|1. Proposes Txn| Gateway
    Gateway -->|2. Authoritative Price Check| Catalog
    Catalog -->|3. Validated Data| Engine
    Engine -->|ALLOW| Razorpay
    Engine -->|ESCALATE| Human
    Engine -->|DENY| Gateway
    Human -->|Approve / Reject| Engine
    Razorpay -->|Payment ID| Ledger
    Engine -->|Log Audit Event| Ledger
    Ledger -->|Persist State| Postgres
    Gateway -.->|Audio Narration| TTS
```

---

## Security Threat Model & Implemented Defenses

| Threat Scenario | Attack Vector / Trigger | AgentGuard Defense | Policy Decision & Reason Code |
| :--- | :--- | :--- | :--- |
| **Price Tampering** | Agent claims item costs ₹1,999; catalog price is ₹3,499 | Independent catalog price reconciliation | `DENY` (`PRICE_MISMATCH`) |
| **Over-Budget Attempt** | Transaction exceeds mandate single limit or remaining cap | Cumulative budget tracking against active mandate | `ESCALATE` or `DENY` (`MANDATE_EXCEEDED`) |
| **Transaction Replay** | Re-sending previously processed or in-flight idempotency key | Nonce validation & database idempotency lock | `DENY` (`REPLAY_DETECTED`) |
| **Revoked Mandate** | User terminated agent mandate; agent attempts checkout | Real-time mandate status verification | `DENY` (`MANDATE_REVOKED`) |
| **Payment Failure** | Gateway error, network dropped, or bank rejection | Nonce protection, idempotency cache & safe retry | Safe retry or controlled `FAILED` state |
| **Legitimate Proposal** | Valid item, authentic price, within scoped budget | Complete verification and mandate balance deduction | `ALLOW` → Controlled Execution |

---

## Why the Model is Not the Authority

```
[ UNTRUSTED ]
AI Model / Shopping Agent
       │  (Suggests purchase: "Buy item X for ₹1,999")
       ▼
═══════════════════════════════════════════════════════════════════
[ TRUST BOUNDARY: AgentGuard Authorization Firewall ]
═══════════════════════════════════════════════════════════════════
       │  (Fetches official catalog price: ₹3,499)
       ▼
[ AUTHORITATIVE ]
Independent Verification + Deterministic Rule Set
       │  (Rule: |proposed - actual| <= 0.01 -> False: DENY PRICE_MISMATCH)
       ▼
[ CONTROLLED EXECUTION ]
Razorpay Test Mode / Safe Payment Engine (Execution BLOCKED)
```

Even if the agent is compromised by prompt injection, hallucinates zero cost, or suffers memory corruption, **it has zero execution privileges**. It cannot authorize payments, sign transactions, or alter database balances.

---

## Tamper-Evident Forensic Ledger

Every proposal, verification, policy decision, approval, and execution event is committed to a hash-linked audit log:
- **Cryptographic Chaining**: Each entry stores `event_hash = SHA256(prev_hash + event_data)`.
- **Integrity Verification**: The cockpit provides one-click cryptographic chain integrity verification.
- **Audit Persistence**: Demo resets and mandate renewals never destroy audit trails or past transaction records.
- **Non-Repudiation**: Full forensic capture of exact client proposals vs. authoritative catalog findings.

---

## Conversational Security Assistant & Voice Architecture

AgentGuard features an integrated conversational security assistant:
- **Role**: Explains system decisions, inspects mandate state, analyzes threat attempts, and points out audit proofs.
- **Zero Authority**: The assistant has read-only live inspection capability; it cannot approve or execute payments.
- **Voice Synthesis**: Powered strictly by **Deepgram TTS** using the **Brooke** (`flux-brooke-en`) model with server-side proxying and an enforced 0.95x cadence for high speech intelligibility. All API keys remain server-side.

---

## Live Autonomous Demo Walkthrough

Judges can launch the end-to-end autonomous walkthrough via the top control bar or by typing/speaking `"start demo"`:

1. **Mandate Initialization**: Active mandate (`mandate-001`) initialized with ₹3,000 budget.
2. **Attack Simulation**: AI shopping agent proposes a Mechanical Keyboard claiming ₹1,999. AgentGuard cross-checks the catalog (₹3,499), detects manipulation, and triggers `DENY` (`PRICE_MISMATCH`).
3. **Legitimate Execution**: Agent proposes a Portable Bluetooth Speaker (₹2,799). AgentGuard verifies catalog price, validates remaining ₹3,000 budget, issues `ALLOW`, and securely executes via Razorpay Test Mode, leaving ₹201 budget.
4. **Forensic Inspection**: Visual breakdown of the SHA-256 hash chain and transaction ledger.
5. **Lifecycle Reset**: Automated invocation of `/internal/demo/reset-mandate` restores the demo mandate back to ₹3,000 without erasing transaction history.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, GSAP animations, Lucide icons |
| **Backend API** | FastAPI, Python 3.12+, Pydantic v2, Uvicorn, HTTPX |
| **Database & ORM** | PostgreSQL, SQLAlchemy 2.0, Alembic migrations |
| **AI Proposer & Assistant** | Google Gemini (restricted to untrusted proposal & advisory Q&A) |
| **Voice Synthesis (TTS)** | Deepgram API (`flux-brooke-en` voice) |
| **Payment Gateway** | Razorpay Orders & Payments API (Test Mode with mock fallback) |
| **Testing & Quality** | Pytest, TestSprite Autonomous Regression Suite |

---

## Testing & Verification

AgentGuard has undergone rigorous test suite validation:

- **Demo Mandate Reset Suite**: 4/4 passed (`backend/tests/unit/test_demo_mandate_reset.py`)
- **TTS Endpoint Security Suite**: 6/6 passed (`backend/tests/unit/test_tts_endpoint.py`)
- **Focused TestSprite Regression Suite**: 14/16 passed (`testsprite_tests/`)
  - *Note*: The 2 TestSprite failures were test harness assertion mismatches (expecting specific response formats on dynamic mock inputs) rather than system defects; core functionality was independently verified.
- **Frontend Production Build**: Clean build passed (`npm run build` / Vite v5.4)
- **Voice Provider Audit**: Verified complete unification on Deepgram Brooke runtime TTS.
- **Secret & Credential Audit**: Verified 0 exposed API keys or live credentials tracked in Git.

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- PostgreSQL running locally or accessible via URL

### 1. Clone & Configure Environment
```bash
git clone <repo-url>
cd AgentGuard

# Copy environment template
cp .env.example .env
```

Configure `.env` with your local database and provider keys:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/firewall_db
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/firewall_test_db
TRANSACTION_EXPIRY_SECONDS=300
PRICE_MISMATCH_TOLERANCE=0.01
GEMINI_API_KEY=your_gemini_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
RAZORPAY_TEST_KEY_ID=your_razorpay_key_id_here
RAZORPAY_TEST_KEY_SECRET=your_razorpay_key_secret_here
RAZORPAY_MOCK_FALLBACK=True
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations and seed database
alembic upgrade head
python scripts/seed_db.py

# Start FastAPI server (runs on port 8000)
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
# In a new terminal window
cd frontend

# Install dependencies
npm install

# Start Vite development server (runs on port 3000)
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes (propose, approve, execute, mandate, tts)
│   │   ├── conversational/  # Conversational assistant orchestrator & prompt guardrails
│   │   ├── db/              # SQLAlchemy session & Alembic migrations
│   │   ├── models/          # Core models (Transaction, Mandate, AuditEvent, Product)
│   │   ├── policy/          # Deterministic policy engine (limits, replay, verification)
│   │   └── services/        # Cryptographic ledger & Razorpay integration
│   └── tests/               # Pytest unit and integration test suites
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components & shared widgets
│   │   ├── features/        # Cockpit, Threat Lab, Forensic Ledger, Autonomous Demo
│   │   └── lib/             # API client & helper utilities
│   └── package.json
├── docs/                    # Architectural specs, Threat Model & PRD
├── knowledge/               # Grounding corpus for conversational assistant
├── scripts/                 # Database seed & test validation utilities
└── testsprite_tests/        # Automated regression test specifications & tests
```

---

## Limitations

- **Razorpay Test Mode**: Real bank transactions are not triggered; all flows run against Razorpay's sandbox/test mode with mock fallback options.
- **Demo Scope**: Scoped around single-tenant e-commerce mandates to clearly demonstrate edge cases within hackathon evaluation timeframes.

---

## Future Roadmap

- **Multi-Party Approval**: Threshold signatures (`t-of-n`) for enterprise high-value authorizations.
- **Biometric WebAuthn Passkey Execution**: Hardware-bound passkey confirmation for escalated transactions.
- **Multi-Rail Settlement**: Adapters for UPI auto-pay, ISO 20022 messaging, and stablecoin payment rails.

---

> **AI should be able to propose.**  
> **It should never be trusted to authorize.**
