"""Pytest Test Knowledge Extractor for AgentGuard Knowledge Pipeline.

Extracts test functions, proven invariants, target modules, and security assertions
from backend/tests/ using Python AST.
"""

import ast
import hashlib
from pathlib import Path

from backend.app.knowledge.models import (
    AuthorityType,
    CodeRelationship,
    DomainCategory,
    FreshnessStatus,
    KnowledgeUnit,
    QAIssue,
    SourceTier,
    TestKnowledgeRecord,
)
from backend.app.knowledge.secret_scanner import SecretScanner


class TestExtractor:
    """Extracts test knowledge records mapping test cases to proven invariants and targets."""

    __test__ = False  # Prevent Pytest from collecting this helper class as a test fixture

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def discover_test_files(self) -> list[Path]:
        """Discovers all test files in backend/tests/."""
        tests_dir = self.workspace_root / "backend" / "tests"
        test_files: list[Path] = []

        if tests_dir.exists():
            for p in sorted(tests_dir.rglob("test_*.py")):
                rel = p.relative_to(self.workspace_root)
                if not SecretScanner.is_path_excluded(rel):
                    test_files.append(p)

        return test_files

    def extract_file(
        self, file_path: Path
    ) -> tuple[list[TestKnowledgeRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Parses a test file using AST and extracts test metadata and knowledge units."""
        rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
        issues: list[QAIssue] = []
        records: list[TestKnowledgeRecord] = []
        units: list[KnowledgeUnit] = []

        if SecretScanner.is_path_excluded(rel_path):
            return records, units, issues

        try:
            raw_code = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="TEST_FILE_READ_ERROR",
                    message=f"Failed to read test file {rel_path}: {exc}",
                    source_path=rel_path,
                )
            )
            return records, units, issues

        clean_code, scan_issues, is_clean = SecretScanner.scan_and_redact(raw_code, rel_path)
        issues.extend(scan_issues)

        try:
            tree = ast.parse(clean_code, filename=rel_path)
        except SyntaxError as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="TEST_AST_SYNTAX_ERROR",
                    message=f"Syntax error in test file {rel_path}:{exc.lineno}: {exc.msg}",
                    source_path=rel_path,
                    line_number=exc.lineno,
                )
            )
            return records, units, issues

        is_integration = "integration" in rel_path
        category = "integration_e2e" if is_integration else "unit_policy"

        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_"):
                docstring = ast.get_docstring(node)
                lines = clean_code.splitlines()[node.lineno - 1 : node.end_lineno]
                snippet = "\n".join(lines)
                fn_hash = hashlib.sha256(snippet.encode("utf-8")).hexdigest()

                # Infer tested invariants and target symbols
                invariants = []
                targets = []
                if "replay" in node.name.lower() or "replay" in (docstring or "").lower():
                    invariants.append("REPLAY_DETECTED (HTTP 409)")
                if "tamper" in node.name.lower() or "price" in node.name.lower():
                    invariants.append("PRICE_MISMATCH (HTTP 403 / DENY)")
                if "budget" in node.name.lower() or "over_budget" in node.name.lower():
                    invariants.append("BUDGET_EXCEEDED (ESCALATE)")
                if "revoke" in node.name.lower():
                    invariants.append("MANDATE_REVOKED (HTTP 403 / DENY)")
                if "chain" in node.name.lower() or "hash" in node.name.lower():
                    invariants.append("SHA-256 Chain Verification")

                # Discover called target functions
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        if child.func.id in ("evaluate_policy", "verify_audit_chain", "log_audit_event", "propose_transaction"):
                            targets.append(child.func.id)

                targets = list(set(targets))

                test_rec = TestKnowledgeRecord(
                    id=f"test_{Path(rel_path).stem}_{node.name}_{fn_hash[:8]}",
                    test_file=rel_path,
                    test_function=node.name,
                    docstring=docstring,
                    test_category=category,
                    target_symbols=targets,
                    invariants_proven=invariants,
                    content_sha256=fn_hash,
                )
                records.append(test_rec)

                relationships = [
                    CodeRelationship(
                        source_symbol=node.name,
                        target_symbol=tgt,
                        relationship_type="TESTS_SYMBOL",
                    )
                    for tgt in targets
                ]

                unit = KnowledgeUnit(
                    id=f"test_{Path(rel_path).stem}_{node.name}_{fn_hash[:8]}",
                    domain=DomainCategory.Y_TEST_SUITES,
                    title=f"Test: {node.name}() in {rel_path}",
                    summary=docstring.split("\n\n")[0] if docstring else f"Automated test {node.name} verifying {', '.join(invariants) or 'system behavior'}",
                    content=(
                        f"Test File: `{rel_path}` (Lines {node.lineno}-{node.end_lineno})\n"
                        f"Test Function: `{node.name}`\n"
                        f"Category: `{category}`\n"
                        f"Docstring: {docstring or 'No docstring provided.'}\n"
                        f"Invariants Proven: {', '.join(invariants) if invariants else 'Standard Contract Verification'}\n"
                        f"Target Symbols: {', '.join(targets) if targets else 'API Integration'}\n\n"
                        f"```python\n{snippet[:1000]}\n```"
                    ),
                    source_type="PYTEST",
                    source_path=rel_path,
                    source_tier=SourceTier.TIER_4_AUTOMATED_TESTS,
                    line_start=node.lineno,
                    line_end=node.end_lineno,
                    symbol=node.name,
                    content_sha256=fn_hash,
                    authority=AuthorityType.SOURCE_DERIVED,
                    freshness=FreshnessStatus.VERIFIED,
                    relationships=relationships,
                    tags=["test", "pytest", category, "test_suites"],
                )
                units.append(unit)

        return records, units, issues

    def extract_all(
        self,
    ) -> tuple[list[TestKnowledgeRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Discovers and extracts all Pytest test cases."""
        files = self.discover_test_files()
        all_records: list[TestKnowledgeRecord] = []
        all_units: list[KnowledgeUnit] = []
        all_issues: list[QAIssue] = []

        for f in files:
            recs, units, issues = self.extract_file(f)
            all_records.extend(recs)
            all_units.extend(units)
            all_issues.extend(issues)

        return all_records, all_units, all_issues
