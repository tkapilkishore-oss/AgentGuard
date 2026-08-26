# SKILLS.md — Agentic Commerce Firewall Tooling & Skills Record

## 1. Mandatory Tooling: Ponytail

- **Status:** Verified and available.
- **Scope:** Globally installed plugin (`~/.gemini/config/plugins/ponytail`).
- **Exact Invokable Skills:**
  - `ponytail` (Switch ponytail intensity level: lite/full/ultra/off)
  - `ponytail-audit` (Audit repo for over-engineering and deletion candidates)
  - `ponytail-gain` (Measured impact scoreboard: code, cost, time saved)
  - `ponytail-help` (Quick reference for ponytail levels and commands)
  - `ponytail-review` (Review diffs/changes for over-engineering)
- **Mandatory Project Rule:**
  - Ponytail MUST be used for EVERY piece of code created, modified, refactored, or generated across all languages (Python, TypeScript, SQL, HTML/CSS, shell scripts, tests, configuration).
  - Principles: YAGNI, standard library first, zero unrequested abstractions, minimal code that works.

---

## 2. Antigravity Awesome Skills Library

- **Source Repository:** `https://github.com/sickn33/antigravity-awesome-skills`
- **Installed Version:** `v13.13.0`
- **Installation Path:** `~/.agents/skills` (installed via `npx antigravity-awesome-skills --antigravity`)
- **Discovery Status:** Fully discoverable by Antigravity IDE and agents.

---

## 3. Approved Project Skill IDs

### Primary Project Bundles & Approved Additions

| Category / Bundle | Skill ID | Purpose in Project |
|---|---|---|
| **Essentials** | `concise-planning` | Atomic, structured planning before non-trivial tasks |
| **Essentials** | `lint-and-validate` | Automated code formatting, syntax, and lint verification |
| **Essentials** | `git-pushing` | Clean version control operations |
| **Essentials** | `kaizen` | Continuous improvement & engineering discipline |
| **Essentials** | `systematic-debugging` | Root-cause diagnostic tracing |
| **Security Engineer** | `ethical-hacking-methodology` | Adversarial mindset for attack vectors |
| **Security Engineer** | `burp-suite-testing` | API security testing patterns |
| **Security Engineer** | `top-web-vulnerabilities` | OWASP API Top 10 alignment |
| **Security Engineer** | `linux-privilege-escalation` | System security assessment |
| **Security Engineer** | `cloud-penetration-testing` | Cloud deployment hardening |
| **Security Engineer** | `security-auditor` | Audit trail & security verification |
| **Security Engineer** | `vulnerability-scanner` | Static & dynamic flaw detection |
| **Security Developer** | `api-security-best-practices` | API authentication & rate limiting principles |
| **Security Developer** | `auth-implementation-patterns` | Nonce, session & mandate protection |
| **Security Developer** | `backend-security-coder` | Parameterized queries & backend defensive coding |
| **Security Developer** | `frontend-security-coder` | XSS & client-side sanitization (Phase 4) |
| **Security Developer** | `cc-skill-security-review` | Pre-commit security checklists |
| **Security Developer** | `pci-compliance` | Payment isolation & secret handling rules |
| **TDD / QA** | `test-driven-development` | Red-Green-Refactor dev loops |
| **TDD / QA** | `python-testing-patterns` | Pytest fixtures & async test patterns |
| **TDD / QA** | `e2e-testing-patterns` | End-to-end integration test structure |
| **TDD / QA** | `debugging-strategies` | Diagnostics & bug isolation |
| **TDD / QA** | `debugging-toolkit` | Smart debugging & log analysis |
| **Web Wizard** | `frontend-design` | UI design tokens & dark-mode security console style |
| **Web Wizard** | `react-best-practices` | React 19 / Next.js performance |
| **Web Wizard** | `react-patterns` | Component architecture |
| **Web Wizard** | `nextjs-best-practices` | Next.js App Router patterns |
| **Web Wizard** | `nextjs-app-router-patterns` | Next.js router conventions |
| **Web Wizard** | `tailwind-patterns` | Dark-mode tailwind styling |
| **Backend & DB** | `api-design-principles` | RESTful API contract discipline |
| **Backend & DB** | `python-fastapi-development` | FastAPI async routing & Pydantic validation |
| **Backend & DB** | `fastapi-pro` | Advanced FastAPI structures |
| **Backend & DB** | `fastapi-templates` | FastAPI project organization |
| **Backend & DB** | `fastapi-router-py` | Modular APIRouter design |
| **Backend & DB** | `database-design` | Postgres ACID relational schema design |
| **Backend & DB** | `postgresql` | PostgreSQL schema & indexing |
| **Backend & DB** | `postgres-best-practices` | Row locks & transaction isolation |
| **Backend & DB** | `sql-pro` | Atomic budget reservation SQL patterns |
| **Payments** | `payment-integration` | Razorpay test-mode API integration (Phase 3) |

---

## 4. Phase-by-Phase Skill Activation Plan

To prevent context window bloat and truncation, skills are activated strictly per phase:

### Phase 0: Contract, Threat Model & Database Schema Verification (Current)
- `concise-planning`
- `security-auditor`
- `api-security-best-practices`
- `api-design-principles`
- `database-design`
- `postgresql`
- `postgres-best-practices`
- `sql-pro`

### Phase 1: Policy Engine (Pure Python + Unit Tests)
- `concise-planning`
- `kaizen`
- `lint-and-validate`
- `systematic-debugging`
- `backend-security-coder`
- `python-fastapi-development`
- `fastapi-pro`
- `test-driven-development`
- `python-testing-patterns`

### Phase 2: FastAPI Endpoints + Integration / Adversarial Security Tests
- `concise-planning`
- `api-security-best-practices`
- `backend-security-coder`
- `auth-implementation-patterns`
- `python-fastapi-development`
- `fastapi-router-py`
- `database-design`
- `postgresql`
- `test-driven-development`
- `e2e-testing-patterns`
- `debugging-strategies`
- `lint-and-validate`

### Phase 3: Razorpay Test-Mode Integration
- `payment-integration`
- `pci-compliance`
- `backend-security-coder`
- `test-driven-development`
- `e2e-testing-patterns`

### Phase 4: Frontend (React / Next.js Chat UI, Decision Trace, Attack Console)
- `frontend-design`
- `react-best-practices`
- `react-patterns`
- `nextjs-best-practices`
- `nextjs-app-router-patterns`
- `tailwind-patterns`
- `frontend-security-coder`
- `e2e-testing-patterns`

### Phase 5: Audit Trail UI & Reconstructable Decision History
- `security-auditor`
- `backend-security-coder`
- `frontend-design`
- `react-best-practices`

### Phase 6: System Polish, Deployment & TestSprite Regression Pass
- `lint-and-validate`
- `e2e-testing-patterns`
- `security-auditor`
- `vulnerability-scanner`

---

## 5. Skills Intentionally Excluded / Deferred

The following categories/skills are **EXCLUDED** from activation to preserve narrow product scope and avoid architectural conflict:
- **No Vector DB / RAG Skills:** (`vector-database-engineer`, `rag-engineer`, `langchain`) — explicitly out of scope per PRD §8.
- **No Multi-Agent Framework Skills:** (`langgraph`, `crewai`, `autogen`) — frozen single firewall boundary design.
- **No Custom Cryptography / Blockchain Skills:** (`blockchain-developer`, `crypto-wallet`) — forbidden by PRD §8.
- **No Alternate Backend Languages:** (`rust-pro`, `golang-pro`, `java-pro`, `elixir-pro`) — project stack is Python/FastAPI.
- **No Marketing / SEO Skills in Early Phases:** Deferred/Excluded as product focus is authorization firewall.

---

## 6. Third-Party Skill Safety & Conflict Analysis

1. **Precedence Rule:** Project documentation (`PRD.md`, `TRD.md`, `ARCHITECTURE.md`, `AGENTS.md`, `PHASE0_CORRECTIONS.md`) ALWAYS takes precedence over third-party skill suggestions.
2. **Framework / Language Safety:** Third-party skills offering Node.js/Express or alternative ORMs are used ONLY for abstract security principles. All implementation MUST use Python 3.12+, FastAPI, and PostgreSQL with SQLAlchemy/asyncpg.
3. **Authorization Authority Safety:** Any third-party skill proposing client-side JWT claims or client-supplied authorization tokens as authoritative is rejected. Server DB row-locking and re-derivation from `products` table are strict requirements.
4. **Mandatory Ponytail Precedence:** All code recommendations from any active skill must pass Ponytail YAGNI scrutiny (no bloated helper classes, standard library first, concise functions).

---

## 7. gstack

- **Repository:** `https://github.com/kimjin8/gstack-antigravity`
- **Installation Status:** Installed and Verified.
- **Installed Version / Commit:** `v1.4.0` (built with `bun 1.4.0`).
- **Installation Location:** `~/.antigravity/skills/gstack`
- **Exact Discovered Workflows:**
  - `review` (`/review`) — Staff Engineer code review & production bug detection
  - `investigate` (`/investigate`) — Systematic root-cause debugging engine
  - `plan-eng-review` (`/plan-eng-review`) — Architecture, state machine & edge-case planning review
  - `qa` (`/qa`) — Interactive Playwright browser QA testing & auto-fixing
  - `qa-only` (`/qa-only`) — Interactive QA testing & bug reporting without auto-fixes
  - `retro` (`/retro`) — Retrospective & delivery health audit
  - `cso` (`/cso`) — OWASP Top 10 + STRIDE threat modeling & security review
  - `ship` (`/ship`) — Test suite execution & PR release preparation
  - `land-and-deploy` (`/land-and-deploy`) — CI/CD merge and deployment verification
  - `careful` (`/careful`) — Destructive command safety guardrails
  - `freeze` (`/freeze`) — Edit directory restriction lock
  - `guard` (`/guard`) — Combined `/careful` + `/freeze` protection
  - `unfreeze` (`/unfreeze`) — Remove edit directory lock
  - `plan-design-review` (`/plan-design-review`) — UI design rating & anti-slop audit
  - `design-consultation` (`/design-consultation`) — Design system consultation
  - `design-review` (`/design-review`) — Visual UI audit & fix execution
  - `canary` (`/canary`) — Post-deployment health monitoring loop
  - `benchmark` (`/benchmark`) — Web Vitals & performance benchmark tool
  - `document-release` (`/document-release`) — Documentation sync & release notes writer
  - `browse` (`/browse`) — Headless Chromium browser automation driver
  - `setup-browser-cookies` (`/setup-cookies`) — Session cookie importer for QA
  - `setup-deploy` (`/setup-deploy`) — Deployment target configurator
  - `gstack-upgrade` (`/gstack-upgrade`) — Self-updater tool
  - `codex` (`/codex`) — Multi-model second opinion review
- **Approved Project Usage (Selective / Phase-Specific):**
  - **Phase 0:** `plan-eng-review`, `review`
  - **Phase 1:** `review`, `investigate`, `retro`
  - **Phase 2:** `review`, `investigate`, `cso`
  - **Phase 3:** `review`, `investigate`, `qa`
  - **Phase 4:** `review`, `qa`, `qa-only`, `investigate`
  - **Phase 5:** `review`, `qa`, `investigate`, `retro`
  - **Phase 6:** `review`, `qa`, `retro`, `ship`, `land-and-deploy` (Phase 6 final release)
- **Intentionally Excluded Workflows:**
  - `office-hours` (`/office-hours`) — Product reframing disabled (project vision is locked).
  - `plan-ceo-review` (`/plan-ceo-review`) — Feature scope expansion disabled (PRD/TRD scope is locked).
  - `autoplan` (`/autoplan`) — Automated multi-persona design expansion disabled.
- **Precedence & Compatibility Guarantee:**
  - **Ponytail Integrity:** Unchanged. All code created/refactored by gstack workflows MUST pass Ponytail YAGNI scrutiny.
  - **Antigravity Awesome Skills:** Untouched (`~/.agents/skills`).
  - **Specification Authority:** `PRD.md`, `TRD.md`, `ARCHITECTURE.md`, `AGENTS.md`, `THREAT_MODEL.md`, `CONVENTIONS.md`, `TEST_PLAN.md` take precedence over any gstack suggestion.
