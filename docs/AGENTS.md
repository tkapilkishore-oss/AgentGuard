# AGENTS.md — Operating Instructions for AI Coding Agents

Read this before writing any code. This file governs how you (the coding agent, e.g. Antigravity) should behave in this repository. It complements PRD.md, TRD.md, ARCHITECTURE.md, and THREAT_MODEL.md — read all of them before starting.

## 1. What is frozen — do not re-litigate these

- **Track:** AI Growth & Agentic Commerce (Razorpay AI Buildathon)
- **Product:** Agentic Commerce Firewall — the firewall is the product, the shopping agent is a reference client
- **Core principle:** the LLM/agent's output is an untrusted claim; the server independently re-derives and re-validates everything
- **The six demo scenarios** in PRD §7.4 — build exactly these, do not add or remove scenarios
- **The explicit cut list** (PRD §8 / ARCHITECTURE §3.3): no vector DB, no LangGraph, no multi-agent architecture, no blockchain, no custom crypto, no risk scoring, no merchant dashboard, no real-money transactions
- **Build order:** backend fully first (through Razorpay test-mode integration), frontend after — do not build UI before the API contract in TRD.md is implemented and tested
- **Tech stack:** Python-majority, FastAPI, PostgreSQL, Gemini API, Razorpay test-mode. React/Next.js only for the frontend.

**If you think one of these should change, stop and flag it explicitly rather than silently deviating.** Say what you'd change and why, and wait for confirmation. Do not just implement a different approach because it seems better mid-task.

## 2. Scope discipline rule

Before adding anything not already specified in PRD/TRD/ARCHITECTURE, ask:
> Does this materially improve one of the six core scenarios without threatening the timeline?

If no — do not build it, even if it seems like a good idea. Flag it as a "possible later addition" instead and move on.

## 3. Build order (see PRD/TRD/ARCHITECTURE for full detail per phase)

1. **Phase 0:** THREAT_MODEL.md, DB schema, full API contract — must be reviewed and locked before any implementation code
2. **Phase 1:** Policy engine (pure Python, no I/O) + unit tests covering all six scenarios + hidden seventh
3. **Phase 2:** Real `/transaction/propose` and `/transaction/execute` endpoints + integration/security tests hitting the real HTTP endpoints with adversarial payloads
4. **Phase 3:** Razorpay test-mode integration, full end-to-end happy path
5. **Phase 4:** Frontend — chat UI, Decision Trace panel, Attack Console
6. **Phase 5:** Audit trail UI
7. **Phase 6:** Polish, deploy, pitch prep

**Each phase must be fully tested and clear of known bugs before starting the next phase.** Do not carry known bugs forward "to fix later."

## 4. Testing requirements (non-negotiable)

- Every phase from Phase 1 onward needs passing tests before being considered done
- Unit tests on the policy engine are necessary but **not sufficient** as a security proof — integration tests must hit the actual running HTTP endpoints with adversarial payloads and assert on real responses
- Never write a test that only asserts against an in-memory function call when the claim being tested is about endpoint-level security behavior
- A full regression test pass (TestSprite) happens once, at the very end, on top of per-phase tests — it does not replace them

## 5. Security implementation rules (apply to all code, every phase)

- Never trust client-supplied price, merchant identity, or quantity for authorization math — only for comparison against authoritative DB values
- Server generates all authoritative IDs (transaction ID, nonce, expiry) — never accept these from a request
- `/transaction/execute` must independently re-validate mandate status, expiry, and price — never trust the propose decision as still valid
- Idempotency must be implemented with real stored response snapshots, not a naive check
- Budget reservation must use real atomic DB operations (row locks / transactions), not read-then-write
- Never expose Razorpay secret keys to the client or to the LLM's context
- Audit log entries are generated server-side only, hash-chained, append-only

## 6. UI rules

- Do not build a flashy, animated, 3D, marketing-style UI. Target aesthetic: Stripe dashboard / Linear / a security console — clean, dark, data-dense
- Motion is only used to represent real state transitions (e.g. a pipeline stage lighting up, a verdict badge flipping) — never decorative
- The Decision Trace panel and Attack Console are the actual point of the frontend — prioritize building these well over any visual polish elsewhere

## 7. Tooling

- Development environment: Google Antigravity (Gemini-3)
- Skill bundles in use from `antigravity-awesome-skills`: **Security Engineer**, **TDD Architect**, **Web Wizard** (frontend phase only), **Essentials**. Do not install or invoke skills outside these bundles for this project without flagging it first.

## 8. When something breaks

Document what broke and how it was fixed — this is expected content for the pitch ("what broke during development and how you recovered"). Don't just silently patch and move on; note it (even briefly, in commit messages or a NOTES.md) so it can be referenced later.