#!/usr/bin/env python
"""CLI Script to build and QA-validate the AgentGuard Knowledge Base."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.knowledge.builder import KnowledgeBuilder
from backend.app.knowledge.models import QAStatus


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentGuard Canonical Knowledge Base Builder")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discovery, extraction, and QA checks without writing files to disk.",
    )
    args = parser.parse_args()

    builder = KnowledgeBuilder(workspace_root=PROJECT_ROOT)
    print(f"[*] Starting AgentGuard Knowledge Build (dry_run={args.dry_run})...")

    manifest, qa_report = builder.build_all(dry_run=args.dry_run)

    print("-" * 60)
    print(f"[*] Build Complete. QA Status: {qa_report.status.value}")
    print(f"[*] Total Knowledge Units: {qa_report.metrics.total_units}")
    print(f"    - Docs Chunks:       {qa_report.metrics.docs_chunks}")
    print(f"    - Python Symbols:    {qa_report.metrics.python_symbols}")
    print(f"    - TSX Components:    {qa_report.metrics.tsx_components}")
    print(f"    - FastAPI Routes:    {qa_report.metrics.api_routes}")
    print(f"    - Pytest Test Cases: {qa_report.metrics.test_cases}")
    print(f"    - Canonical Facts:   {qa_report.metrics.canonical_facts}")
    print(f"[*] Domains Covered:     {qa_report.metrics.domains_covered} / 31")
    print(f"[*] Secret Scan Clean:   {qa_report.secret_scan_clean}")
    print(f"[*] QA Issues Detected:  {len(qa_report.issues)}")
    print("-" * 60)

    if qa_report.status == QAStatus.INVALID:
        print("[!] QA Validation FAILED with critical errors:")
        for issue in qa_report.issues:
            if issue.severity.value == "ERROR":
                print(f"    - [{issue.code}] {issue.message} ({issue.source_path or 'N/A'})")
        return 1
    elif qa_report.status == QAStatus.VALID_WITH_WARNINGS:
        print("[*] QA Validation passed with warnings.")
        for issue in qa_report.issues:
            if issue.severity.value == "WARNING":
                print(f"    - (WARN) [{issue.code}] {issue.message}")
        return 0
    else:
        print("[*] QA Validation 100% CLEAN. Knowledge base is valid.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
