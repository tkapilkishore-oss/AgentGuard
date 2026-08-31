#!/usr/bin/env python
"""CLI Script to validate existing AgentGuard Knowledge Base assets."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.knowledge.validator import KnowledgeValidator


def main() -> int:
    validator = KnowledgeValidator(workspace_root=PROJECT_ROOT)
    is_valid, errors = validator.validate()

    if is_valid:
        print("[PASS] Knowledge base assets are structurally valid, complete, and secret-clean.")
        return 0
    else:
        print("[FAIL] Knowledge base validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
