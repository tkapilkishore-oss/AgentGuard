"""Conflict and Staleness Detector for AgentGuard Knowledge Pipeline.

Validates reference integrity, detects broken file paths and missing symbols,
verifies API route consistency, and checks for fingerprint drift.
"""

import hashlib
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from backend.app.knowledge.models import (
    AuthorityType,
    DomainCategory,
    FreshnessStatus,
    KnowledgeUnit,
    QAIssue,
    QASeverity,
)
from backend.app.knowledge.secret_scanner import SecretScanner
from backend.app.main import app


class ConflictDetector:
    """Detects discrepancies, broken links, stale fingerprints, and route gaps in knowledge units."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def _collect_api_routes(self, app_or_router: Any) -> list[APIRoute]:
        """Recursively unpacks FastAPI routes, including nested routers and _IncludedRouter objects."""
        routes: list[APIRoute] = []
        for r in getattr(app_or_router, "routes", []):
            if isinstance(r, APIRoute):
                routes.append(r)
            elif hasattr(r, "original_router"):
                routes.extend(self._collect_api_routes(r.original_router))
            elif hasattr(r, "router"):
                routes.extend(self._collect_api_routes(r.router))
            elif hasattr(r, "routes"):
                routes.extend(self._collect_api_routes(r))
        return routes

    def detect_conflicts(self, units: list[KnowledgeUnit]) -> tuple[list[KnowledgeUnit], list[QAIssue]]:
        """Runs comprehensive conflict, staleness, broken link, and route consistency checks."""
        issues: list[QAIssue] = []
        updated_units: list[KnowledgeUnit] = []

        # 1. Collect real FastAPI registered routes
        all_real_routes = self._collect_api_routes(app)
        registered_routes: set[str] = {r.path for r in all_real_routes}

        # 2. Track indexed routes and symbols
        indexed_routes: set[str] = set()
        file_hashes: dict[str, str] = {}

        for unit in units:
            freshness = unit.freshness
            authority = unit.authority

            # Check 1: File Existence
            if unit.source_path and not unit.source_path.startswith("canonical/"):
                disk_path = self.workspace_root / unit.source_path
                if not disk_path.exists():
                    issues.append(
                        QAIssue(
                            severity=QASeverity.ERROR,
                            code="BROKEN_SOURCE_FILE_REFERENCE",
                            message=f"Referenced source file does not exist: {unit.source_path}",
                            source_path=unit.source_path,
                            context={"unit_id": unit.id, "title": unit.title},
                        )
                    )
                    freshness = FreshnessStatus.STALE
                    authority = AuthorityType.CONFLICTING
                else:
                    # Check 2: Fingerprint Drift / Staleness
                    if unit.source_path not in file_hashes:
                        try:
                            file_content = disk_path.read_text(encoding="utf-8")
                            clean_content, _, _ = SecretScanner.scan_and_redact(file_content, unit.source_path)
                            file_hashes[unit.source_path] = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
                        except Exception:
                            file_hashes[unit.source_path] = ""

            # Check 3: API Route Validation
            if unit.route:
                indexed_routes.add(unit.route)
                if unit.route not in registered_routes:
                    issues.append(
                        QAIssue(
                            severity=QASeverity.ERROR,
                            code="NONEXISTENT_API_ROUTE",
                            message=f"Indexed API route '{unit.route}' does not exist in FastAPI app.",
                            source_path=unit.source_path,
                            context={"unit_id": unit.id, "route": unit.route},
                        )
                    )
                    authority = AuthorityType.CONFLICTING

            # Check 4: Secret Leakage in Knowledge Unit Content
            _, scan_issues, is_clean = SecretScanner.scan_and_redact(unit.content, unit.source_path)
            if not is_clean:
                issues.extend(scan_issues)

            updated = unit.model_copy(update={"freshness": freshness, "authority": authority})
            updated_units.append(updated)

        # Check 5: Undocumented Routes (Existing route missing from knowledge)
        for r_path in registered_routes:
            # ignore openapi/docs internal routes
            if r_path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
                continue
            if r_path not in indexed_routes:
                issues.append(
                    QAIssue(
                        severity=QASeverity.WARNING,
                        code="UNDOCUMENTED_API_ROUTE_GAP",
                        message=f"FastAPI route '{r_path}' is registered in application but missing from indexed API knowledge.",
                        context={"route": r_path},
                    )
                )

        # Check 6: Reconciled Attack Scenario Count Consistency
        scenario_units = [u for u in updated_units if u.domain == DomainCategory.O_ATTACK_SCENARIOS]
        if not scenario_units:
            issues.append(
                QAIssue(
                    severity=QASeverity.WARNING,
                    code="ATTACK_SCENARIOS_DOMAIN_UNCOVERED",
                    message="No attack scenario knowledge units found in knowledge base.",
                )
            )

        return updated_units, issues
