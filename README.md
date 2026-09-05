# AgentGuard

> **The model is allowed to be wrong. It's not allowed to be authoritative.**

AgentGuard is a deterministic authorization firewall between untrusted AI agents and financial execution. The agent may propose a transaction, but it cannot authorize or execute financial actions directly. AgentGuard independently verifies authoritative transaction data, evaluates a scoped mandate using deterministic policy, and produces an explicit `ALLOW`, `ESCALATE`, or `DENY` decision before controlled execution.

---

## 🌐 Live Demo

**Production URL:** [https://agentguard-2.onrender.com](https://agentguard-2.onrender.com)

The complete AgentGuard application—including the interactive React frontend, FastAPI authorization engine, tamper-evident forensic ledger, and Deepgram Brooke voice synthesis—is deployed and running live as a unified service on Render.

> **Judge Note:** You only need this single public URL to evaluate AgentGuard. The React frontend is built during deployment and served directly by the FastAPI backend in the same container. No installation, accounts, or local configuration are required.

---

## ⚡ Judge Quick Start (5-Minute Demo)

To experience the full AgentGuard authorization firewall in under five minutes:

1. **Open the Application**: Navigate to [https://agentguard-2.onrender.com](https://agentguard-2.onrender.com).
2. **Start the Conversational Security Assistant**: Click the audio/chat assistant floating badge or open the assistant drawer.
3. **Trigger the Walkthrough**: Click **"Start Guided Tour"** or say / type:
   > *"Give me a demo."*
4. **Watch the Autonomous Walkthrough**:
   - The autonomous demo orchestrates real UI navigation across the live Cockpit and Threat Lab.
   - The visual **AgentCursor** guides you through real backend API interactions with live endpoints.
   - **Scenario 3 — Price Tampering Attack**: Watch the agent propose a Mechanical Keyboard for ₹1,999. AgentGuard independently queries the catalog (authoritative price: ₹3,499), detects the tampering via the visual side-by-side **"LLM Lies"** comparison trace, and issues a deterministic `DENY (PRICE_MISMATCH)`.
   - **Scenario 1 — Legitimate Execution**: An authentic item (₹2,799) is verified against the catalog, validated within the ₹3,000 mandate, approved with `ALLOW`, executed idempotently against Razorpay Test Mode, and committed to the cryptographic ledger.
   - **Threat Scenarios**: Explore the six frozen scenarios in the Threat Lab (Happy Path, Over-Budget Escalation, Price Tampering, Replay Attack Defense, Safe Failure & Retry, Mid-Session Revocation).
   - **Interactive Controls**: You can pause, resume, or stop the walkthrough at any time using the playback controls in the top bar.
5. **Inspect the Forensic Ledger**:
   - Navigate to the **Forensic Ledger** tab to inspect the tamper-evident `SHA-256` cryptographic hash chain and run the one-click chain integrity verification.
6. **Controlled Baseline Reset**:
   - At demo completion, the system automatically triggers `/internal/demo/reset-mandate` to restore the active demo mandate (`mandate-001`) back to its initial ₹3,000 budget without erasing transaction records or audit history.

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

## Production Architecture & Deployment

AgentGuard is deployed in production on **Render** as a single unified Web Service backed by a managed PostgreSQL database.

```
GitHub repository
    ↓
Render Web Service (Single Public URL)
    ↓
FastAPI backend + built React frontend
    ↓
Render PostgreSQL (Managed Database)
```

### Key Architectural Properties

1. **Single Public URL**: The frontend and backend are deployed together in the **same Render Web Service**. Judges and users need only one URL: [https://agentguard-2.onrender.com](https://agentguard-2.onrender.com).
2. **Unified Container Serving**: During deployment, the React frontend is compiled (`npm run build`) and its static production build is served directly by the FastAPI backend application.
3. **No Separate Frontend Hosting**: There is **no separate Vercel deployment** and no separate frontend domain. All API requests (`/api/*`, `/health`, `/internal/*`) and frontend assets are resolved on the same origin, eliminating cross-origin configuration friction.
4. **Managed PostgreSQL**: A separate managed **Render PostgreSQL** database instance handles persistence (transactions, active mandates, catalog products, and the tamper-evident forensic ledger). The database is private to the Render internal network and is **not exposed to judges or the public internet**.

### Architectural Dataflow Diagram

```mermaid
flowchart TD
    subgraph Untrusted Layer
        Agent["Autonomous AI Agent / Gemini Proposer"]
    end

    subgraph Render Web Service ["Render Web Service (agentguard-2.onrender.com)"]
        SPA["React 18 SPA (Built Static Assets)"]
        Gateway["FastAPI API Gateway (/api)"]
        Catalog["Authoritative Product & Merchant Catalog"]
        Engine["Deterministic Policy Engine"]
        Human["Human-in-the-Loop Escalation Chamber"]
        Ledger["Forensic Ledger (SHA-256 Hash Chaining)"]
    end

    subgraph Render Managed Database
        Postgres[("Render PostgreSQL")]
    end

    subgraph External Execution & Voice
        Razorpay["Razorpay Gateway (Test Mode)"]
        Deepgram["Deepgram Brooke TTS (flux-brooke-en)"]
    end

    SPA <-->|In-Origin API Calls| Gateway
    Agent -->|1. Proposes Txn| Gateway
    Gateway -->|2. Authoritative Price Check| Catalog
    Catalog -->|3. Validated Data| Engine
    Engine -->|ALLOW| Razorpay
    Engine -->|ESCALATE| Human
    Engine -->|DENY| Gateway
    Human -->|Approve / Reject| Engine
    Razorpay -->|Payment ID| Ledger
    Engine -->|Log Audit Event| Ledger
    Ledger <-->|Persist State| Postgres
    Gateway -.->|Synthesize Audio| Deepgram
```

---

## Production Render Configuration

For transparent evaluation and reproduction, the production deployment is configured as follows on Render:

| Setting | Production Configuration |
| :--- | :--- |
| **Service Type** | Web Service |
| **Runtime** | Python 3.12+ with Node.js build tooling |
| **Root Directory** | *(empty / repository root)* |
| **Build Command** | `pip install -r backend/requirements.txt && alembic upgrade head && python scripts/seed_db.py && cd frontend && npm install && npm run build` |
| **Start Command** | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |
| **Public Application URL** | `https://agentguard-2.onrender.com` |

> [!NOTE]
> All sensitive credentials (API keys and database credentials) are configured exclusively through the Render Dashboard Environment Variables. No production secrets or live keys are committed to Git.

### Production Environment Variables

The following environment variables are configured in the Render Web Service by name:

- `DATABASE_URL` — Connection URI pointing to the managed Render PostgreSQL instance in production.
- `RAZORPAY_TEST_KEY_ID` — Razorpay Test Mode Key ID.
- `RAZORPAY_TEST_KEY_SECRET` — Razorpay Test Mode Key Secret.
- `GEMINI_API_KEY` — Google Gemini API key for untrusted proposal generation and conversational assistant explanations.
- `DEEPGRAM_API_KEY` — Deepgram API key for server-side audio synthesis.
- `RAZORPAY_MOCK_FALLBACK` — Set to `True` for resilient sandbox fallback during payment gateway downtime.

*(Note: Cartesia has been completely removed from the system. No Cartesia credentials or dependencies are used.)*

---

## Security Threat Model & Implemented Defenses

AgentGuard implements deterministic defenses against six core adversarial scenarios, plus the emergent visual "LLM Lies" comparison trace:

| Threat Scenario | Attack Vector / Trigger | AgentGuard Defense | Policy Decision & Reason Code |
| :--- | :--- | :--- | :--- |
| **1. Legitimate Proposal** | Valid item, authentic price, within scoped budget | Complete verification and mandate balance deduction | `ALLOW` → Controlled Execution |
| **2. Over-Budget Escalation** | Transaction exceeds mandate single limit or remaining cap | Cumulative budget tracking against active mandate | `ESCALATE` or `DENY` (`MANDATE_EXCEEDED`) |
| **3. Price Tampering** | Agent claims item costs ₹1,999; catalog price is ₹3,499 | Independent catalog price reconciliation | `DENY` (`PRICE_MISMATCH`) |
| **4. Transaction Replay** | Re-sending previously processed or in-flight idempotency key | Nonce validation & database idempotency lock | `DENY` (`REPLAY_DETECTED` / 409) |
| **5. Safe Failure & Retry** | Gateway error, network dropped, or bank rejection | Nonce protection, idempotency cache & safe retry | Safe retry or controlled `FAILED` state |
| **6. Mid-Session Revocation** | User terminated agent mandate; agent attempts checkout | Real-time mandate status verification | `DENY` (`MANDATE_REVOKED` / 403) |
| **Emergent: "LLM Lies" Trace** | Agent fabricates prices or discounts to fit under budget caps | Authoritative catalog side-by-side comparison trace | Visual telemetry & forensic flag |

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
- **Zero Authority**: The assistant operates strictly in an advisory and inspection capacity. It can explain policy decisions, inspect mandate health, and analyze audit proofs, but it **cannot authorize, alter, or execute payments**.
- **Sole TTS Provider — Deepgram Brooke**: Text-to-speech audio synthesis is powered exclusively by **Deepgram TTS** using the **Brooke** (`flux-brooke-en`) voice model.
- **Cadence Optimization**: Audio is synthesized with an enforced 0.95x playback cadence for crisp intelligibility during live security demonstrations.
- **Unified Voice System**: Both the interactive security chatbot and the autonomous demo walkthrough utilize this same unified Deepgram voice pipeline.
- **Complete Cartesia Removal**: Cartesia TTS has been completely removed from both backend routes and frontend clients; zero legacy TTS dependencies remain.
- **Secure Server-Side Proxying**: All audio generation requests are proxied through `/api/tts/speak`, ensuring that `DEEPGRAM_API_KEY` is never exposed to the client.

---

## Autonomous Demo Walkthrough

The live autonomous walkthrough demonstrates AgentGuard's defenses against real attacks in real-time. Crucially, **the autonomous demo runs against the real deployed FastAPI backend and database**—it is not a canned or prerecorded mock animation.

### Key Capabilities & Mechanics

- **Semantic Demo Trigger**: Can be started via the UI button or by naturally speaking/typing *"Give me a demo"* to the assistant.
- **Deterministic Orchestration**: State-machine-driven sequence guiding the user through the live Cockpit, Threat Lab, and Forensic Ledger.
- **Real UI Navigation**: Navigates between real application views and inputs actual data.
- **Real Backend Decisions**: Each transaction proposal hits the real `/api/propose` endpoint, triggering real independent catalog reconciliation and real `ALLOW`, `DENY`, and `ESCALATE` policy evaluations.
- **Visual AgentCursor Overlay**: A simulated agent cursor renders on screen to show what the agent is attempting to interact with, providing intuitive visual telemetry.
- **Interactive Controls**: Full pause, resume, and stop controls allow evaluators to halt narration and explore the state manually.
- **Controlled Demo Lifecycle Reset**: Upon demo completion, the system invokes `/internal/demo/reset-mandate` to restore the demo mandate (`mandate-001`) back to its initial ₹3,000 budget, guaranteeing a fresh baseline for the next judge without wiping audit history.
- **Zero Agent Authority**: Even during the autonomous demo, the driving agent possesses zero financial authority; every action is subject to the firewall's policy enforcement.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, GSAP animations, Lucide icons |
| **Backend API** | FastAPI, Python 3.12+, Pydantic v2, Uvicorn, HTTPX |
| **Database & ORM** | PostgreSQL (Render Managed), SQLAlchemy 2.0, Alembic migrations |
| **Hosting & Deployment** | Render Web Service (unified backend + built React frontend) |
| **AI Proposer & Assistant** | Google Gemini (restricted to untrusted proposal & advisory Q&A) |
| **Voice Synthesis (TTS)** | Deepgram API (`flux-brooke-en` Brooke voice at 0.95x cadence) |
| **Payment Gateway** | Razorpay Orders & Payments API (Test Mode with mock fallback) |
| **Testing & Quality** | Pytest, TestSprite Autonomous Regression Suite |

---

## Testing & Verification

AgentGuard has been rigorously validated across unit, integration, and autonomous regression suites:

- **Demo Mandate Reset Suite**: 4/4 passed (`backend/tests/unit/test_demo_mandate_reset.py`)
- **TTS Endpoint Security Suite**: 6/6 passed (`backend/tests/unit/test_tts_endpoint.py`)
- **Autonomous TestSprite Regression Suite**: 14/16 passed (`testsprite_tests/`)
  - **16 tests executed**, **14 passed**, **2 failed**, **0 blocked / flaky**.
  - *Failure Analysis*: The 2 failures were due to test harness assertion mismatches (the harness expected specific response formats on dynamic mock inputs) rather than system functional defects. No real functional or security defect was identified.
- **Manual End-to-End Verification**: Complete verification of the conversational assistant, autonomous walkthrough, Threat Lab scenarios, and mandate reset was manually verified on the live production deployment.
- **Frontend Production Build**: Clean build passed (`npm run build` / Vite v5.4).
- **Voice Provider Audit**: Verified complete unification on Deepgram Brooke TTS with 0 Cartesia references.
- **Secret & Credential Audit**: Verified 0 exposed API keys or live credentials tracked in Git.

---

## Deployment Modes: Production vs. Local Development

### Production (Render)
- **Architecture**: Single Render Web Service running FastAPI, serving the compiled React frontend, connected to a private Render PostgreSQL instance.
- **Live URL**: [https://agentguard-2.onrender.com](https://agentguard-2.onrender.com)
- **Serving**: Static files served by FastAPI at root `/`; API mounted at `/api`.

### Local Development Setup

The existing local setup remains fully supported for local development and debugging:

#### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- PostgreSQL running locally or accessible via URL

#### 1. Clone & Configure Environment
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

#### 2. Backend Setup
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

#### 3. Frontend Setup
```bash
# In a new terminal window
cd frontend

# Install dependencies
npm install

# Start Vite development server (runs on port 3000 with proxy to localhost:8000)
npm run dev
```

Open `http://localhost:3000` in your browser for local development.

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
