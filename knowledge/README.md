# AgentGuard Knowledge Base

Validated, versioned knowledge repository for the AgentGuard Conversational Brain.

## Manifest Summary
- **Version**: `5.5B-1.0.0`
- **QA Status**: `VALID`
- **Total Knowledge Units**: `908`
- **Built At**: `2026-09-05T17:15:58.567764+00:00`

## Directory Layout
- `canonical/`: Authoritative facts and domain classifications.
- `generated/`: Deterministically extracted documentation, code symbols, routes, and UI actions.
- `qa/`: Latest machine-readable and markdown validation reports.
- `schemas/`: Pydantic & JSON schemas for all knowledge units.

## Commands
- **Build Knowledge Base**: `python scripts/build_knowledge.py`
- **Validate Knowledge Base**: `python scripts/validate_knowledge.py`
