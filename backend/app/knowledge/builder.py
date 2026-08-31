"""Master Knowledge Builder for AgentGuard Knowledge Pipeline.

Orchestrates doc ingestion, AST parsing, TSX extraction, route introspection,
test mapping, canonical fact generation, relationship linking, secret scanning,
QA conflict detection, and deterministic dataset persistence.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.knowledge.api_extractor import ApiExtractor
from backend.app.knowledge.ast_extractor import CodeAstExtractor
from backend.app.knowledge.canonical_facts import CanonicalFactsBuilder
from backend.app.knowledge.conflict_detector import ConflictDetector
from backend.app.knowledge.doc_ingestor import DocIngestor
from backend.app.knowledge.frontend_extractor import FrontendExtractor
from backend.app.knowledge.models import (
    CoverageMetrics,
    KnowledgeManifest,
    KnowledgeUnit,
    QAIssue,
    QAReport,
    QASeverity,
    QAStatus,
)
from backend.app.knowledge.relationships import RelationshipLinker
from backend.app.knowledge.test_extractor import TestExtractor


class KnowledgeBuilder:
    """Master orchestrator for knowledge extraction, QA validation, and asset persistence."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path(__file__).resolve().parents[3]
        self.knowledge_dir = self.workspace_root / "knowledge"

    def build_all(self, dry_run: bool = False) -> tuple[KnowledgeManifest, QAReport]:
        """Executes full knowledge extraction, secret scanning, QA validation, and persistence."""
        all_issues: list[QAIssue] = []
        all_units: list[KnowledgeUnit] = []

        # 1. Document Ingestion (docs/*.md)
        doc_ingestor = DocIngestor(self.workspace_root)
        doc_units, doc_issues = doc_ingestor.ingest_all()
        all_units.extend(doc_units)
        all_issues.extend(doc_issues)

        # 2. Python AST Code Extraction
        ast_extractor = CodeAstExtractor(self.workspace_root)
        code_symbols, code_units, code_issues = ast_extractor.extract_all()
        all_units.extend(code_units)
        all_issues.extend(code_issues)

        # 3. TypeScript / TSX Frontend Extraction
        fe_extractor = FrontendExtractor(self.workspace_root)
        fe_actions, fe_units, fe_issues = fe_extractor.extract_all()
        all_units.extend(fe_units)
        all_issues.extend(fe_issues)

        # 4. FastAPI Route Introspection
        api_extractor = ApiExtractor(self.workspace_root)
        api_routes, api_units, api_issues = api_extractor.extract_routes()
        all_units.extend(api_units)
        all_issues.extend(api_issues)

        # 5. Pytest Test Extraction
        test_extractor = TestExtractor(self.workspace_root)
        test_records, test_units, test_issues = test_extractor.extract_all()
        all_units.extend(test_units)
        all_issues.extend(test_issues)

        # 6. Canonical Facts Generation
        canonical_facts, canonical_units = CanonicalFactsBuilder.build_facts()
        all_units.extend(canonical_units)

        # 7. Cross-Reference Relationship Linking
        linked_units = RelationshipLinker.enrich_relationships(all_units)

        # 8. Conflict, Broken Link & Staleness Detection
        conflict_detector = ConflictDetector(self.workspace_root)
        verified_units, conflict_issues = conflict_detector.detect_conflicts(linked_units)
        all_issues.extend(conflict_issues)

        # 9. Evaluate Domain Coverage
        domain_coverage = CanonicalFactsBuilder.evaluate_domain_coverage(verified_units)
        covered_count = sum(1 for status in domain_coverage.values() if status.value in ("COVERED", "PARTIALLY_COVERED"))
        gap_count = sum(1 for status in domain_coverage.values() if status.value == "KNOWLEDGE_GAP")

        # 10. Compute Metrics
        metrics = CoverageMetrics(
            total_units=len(verified_units),
            docs_chunks=len(doc_units),
            python_symbols=len(code_symbols),
            tsx_components=len(fe_units),
            api_routes=len(api_routes),
            test_cases=len(test_records),
            canonical_facts=len(canonical_facts),
            domains_covered=covered_count,
            domains_gap=gap_count,
            unresolved_references=sum(1 for i in all_issues if i.code == "BROKEN_SOURCE_FILE_REFERENCE"),
            conflicts_detected=sum(1 for i in all_issues if i.severity == QASeverity.ERROR),
            stale_records=sum(1 for u in verified_units if u.freshness.value == "STALE"),
        )

        # 11. Determine Overall QA Status
        has_errors = any(i.severity == QASeverity.ERROR for i in all_issues)
        has_warnings = any(i.severity == QASeverity.WARNING for i in all_issues)

        if has_errors:
            qa_status = QAStatus.INVALID
        elif has_warnings:
            qa_status = QAStatus.VALID_WITH_WARNINGS
        else:
            qa_status = QAStatus.VALID

        now_iso = datetime.now(timezone.utc).isoformat()

        # 12. Build QA Report
        qa_report = QAReport(
            status=qa_status,
            generated_at=now_iso,
            commit_fingerprint="frozen_recovery_point_phase5.5a",
            metrics=metrics,
            issues=all_issues,
            domain_coverage={k: v.value for k, v in domain_coverage.items()},  # type: ignore
            secret_scan_clean=not any(i.code == "CONFIDENTIAL_SECRET_DETECTED" for i in all_issues),
        )

        # 13. Build Manifest
        manifest = KnowledgeManifest(
            version="5.5B-1.0.0",
            status=qa_status,
            built_at=now_iso,
            commit_sha="frozen_recovery_point_phase5.5a",
            content_sha256="",
            metrics=metrics,
            dataset_files={},
        )

        # 14. Persist datasets to knowledge/ if not dry-run
        if not dry_run:
            self._persist_assets(
                manifest=manifest,
                qa_report=qa_report,
                doc_units=doc_units,
                code_symbols=code_symbols,
                fe_actions=fe_actions,
                api_routes=api_routes,
                test_records=test_records,
                canonical_facts=canonical_facts,
                verified_units=verified_units,
                domain_coverage=domain_coverage,
            )

        return manifest, qa_report

    def _persist_assets(
        self,
        manifest: KnowledgeManifest,
        qa_report: QAReport,
        doc_units: list[KnowledgeUnit],
        code_symbols: list,
        fe_actions: list,
        api_routes: list,
        test_records: list,
        canonical_facts: list,
        verified_units: list[KnowledgeUnit],
        domain_coverage: dict,
    ) -> None:
        """Writes structured JSON datasets and QA reports to knowledge/."""
        canonical_dir = self.knowledge_dir / "canonical"
        generated_dir = self.knowledge_dir / "generated"
        qa_dir = self.knowledge_dir / "qa"
        schemas_dir = self.knowledge_dir / "schemas"

        for d in (canonical_dir, generated_dir, qa_dir, schemas_dir):
            d.mkdir(parents=True, exist_ok=True)

        # 1. Canonical facts & domains
        self._write_json(canonical_dir / "facts.json", [f.model_dump() for f in canonical_facts])
        self._write_json(
            canonical_dir / "domains.json",
            {k: v.value for k, v in domain_coverage.items()},
        )

        # 2. Generated datasets
        self._write_json(generated_dir / "docs_chunks.json", [u.model_dump() for u in doc_units])
        self._write_json(generated_dir / "code_symbols.json", [s.model_dump() for s in code_symbols])
        self._write_json(generated_dir / "frontend_ui.json", [a.model_dump() for a in fe_actions])
        self._write_json(generated_dir / "api_routes.json", [r.model_dump() for r in api_routes])
        self._write_json(generated_dir / "test_knowledge.json", [t.model_dump() for t in test_records])
        self._write_json(generated_dir / "unified_knowledge.json", [u.model_dump() for u in verified_units])

        # 3. QA Reports (JSON & Markdown)
        self._write_json(qa_dir / "latest_report.json", qa_report.model_dump())
        self._write_markdown_qa_report(qa_dir / "latest_report.md", qa_report)

        # 4. Manifest
        manifest_path = self.knowledge_dir / "manifest.json"
        self._write_json(manifest_path, manifest.model_dump())

        # 5. README.md
        self._write_readme(self.knowledge_dir / "README.md", manifest)

    def _write_json(self, path: Path, data: Any) -> None:
        """Writes deterministically sorted and indented JSON."""
        content = json.dumps(data, indent=2, sort_keys=True)
        path.write_text(content + "\n", encoding="utf-8")

    def _write_markdown_qa_report(self, path: Path, report: QAReport) -> None:
        """Writes a human-readable QA report in markdown."""
        md_lines = [
            "# AgentGuard Knowledge QA & Validation Report",
            "",
            f"- **Status**: `{report.status.value}`",
            f"- **Generated At**: `{report.generated_at}`",
            f"- **Secret Scan Clean**: `{'PASS' if report.secret_scan_clean else 'FAIL'}`",
            "",
            "## Coverage Metrics",
            "",
            f"- **Total Knowledge Units**: `{report.metrics.total_units}`",
            f"- **Documentation Chunks**: `{report.metrics.docs_chunks}`",
            f"- **Python Code Symbols**: `{report.metrics.python_symbols}`",
            f"- **TypeScript / TSX Components**: `{report.metrics.tsx_components}`",
            f"- **FastAPI API Routes**: `{report.metrics.api_routes}`",
            f"- **Pytest Test Cases**: `{report.metrics.test_cases}`",
            f"- **Canonical Facts**: `{report.metrics.canonical_facts}`",
            f"- **Domains Covered**: `{report.metrics.domains_covered} / 31`",
            f"- **Domain Knowledge Gaps**: `{report.metrics.domains_gap}`",
            f"- **Unresolved References**: `{report.metrics.unresolved_references}`",
            f"- **Conflicts Detected**: `{report.metrics.conflicts_detected}`",
            "",
            "## QA Issues & Discrepancies",
            "",
        ]

        if not report.issues:
            md_lines.append("Zero QA issues or discrepancies detected. Knowledge base is 100% clean.")
        else:
            md_lines.append("| Severity | Code | Message | Source Path |")
            md_lines.append("|---|---|---|---|")
            for issue in report.issues:
                md_lines.append(
                    f"| `{issue.severity.value}` | `{issue.code}` | {issue.message} | `{issue.source_path or 'N/A'}` |"
                )

        path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    def _write_readme(self, path: Path, manifest: KnowledgeManifest) -> None:
        """Writes the knowledge directory README."""
        content = f"""# AgentGuard Knowledge Base

Validated, versioned knowledge repository for the AgentGuard Conversational Brain.

## Manifest Summary
- **Version**: `{manifest.version}`
- **QA Status**: `{manifest.status.value}`
- **Total Knowledge Units**: `{manifest.metrics.total_units}`
- **Built At**: `{manifest.built_at}`

## Directory Layout
- `canonical/`: Authoritative facts and domain classifications.
- `generated/`: Deterministically extracted documentation, code symbols, routes, and UI actions.
- `qa/`: Latest machine-readable and markdown validation reports.
- `schemas/`: Pydantic & JSON schemas for all knowledge units.

## Commands
- **Build Knowledge Base**: `python scripts/build_knowledge.py`
- **Validate Knowledge Base**: `python scripts/validate_knowledge.py`
"""
        path.write_text(content, encoding="utf-8")
