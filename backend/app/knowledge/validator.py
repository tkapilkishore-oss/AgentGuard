"""Standalone Knowledge Validator for AgentGuard Knowledge Pipeline.

Validates existing knowledge assets without rebuilding, ensuring schema conformance,
zero secret leakage, and valid QA report status.
"""

import json
import sys
from pathlib import Path

from backend.app.knowledge.models import (
    KnowledgeManifest,
    KnowledgeUnit,
    QAReport,
    QAStatus,
)
from backend.app.knowledge.secret_scanner import SecretScanner


class KnowledgeValidator:
    """Validates already-generated knowledge assets."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path(__file__).resolve().parents[3]
        self.knowledge_dir = self.workspace_root / "knowledge"

    def validate(self) -> tuple[bool, list[str]]:
        """Validates existing knowledge assets on disk.

        Returns (is_valid: bool, error_messages: list[str]).
        """
        errors: list[str] = []

        manifest_file = self.knowledge_dir / "manifest.json"
        if not manifest_file.exists():
            return False, ["Missing knowledge manifest: knowledge/manifest.json not found."]

        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest = KnowledgeManifest.model_validate(manifest_data)
        except Exception as exc:
            return False, [f"Invalid manifest.json schema: {exc}"]

        if manifest.status == QAStatus.INVALID:
            errors.append("Manifest status is INVALID.")
        elif manifest.status == QAStatus.BUILDING:
            errors.append("Manifest status is BUILDING (incomplete build).")

        # Verify required dataset files
        required_files = [
            self.knowledge_dir / "canonical" / "facts.json",
            self.knowledge_dir / "canonical" / "domains.json",
            self.knowledge_dir / "generated" / "docs_chunks.json",
            self.knowledge_dir / "generated" / "code_symbols.json",
            self.knowledge_dir / "generated" / "api_routes.json",
            self.knowledge_dir / "generated" / "frontend_ui.json",
            self.knowledge_dir / "generated" / "test_knowledge.json",
            self.knowledge_dir / "generated" / "unified_knowledge.json",
            self.knowledge_dir / "qa" / "latest_report.json",
            self.knowledge_dir / "qa" / "latest_report.md",
        ]

        for rf in required_files:
            if not rf.exists():
                errors.append(f"Required knowledge dataset missing: {rf.relative_to(self.workspace_root)}")

        # Validate unified knowledge records
        unified_path = self.knowledge_dir / "generated" / "unified_knowledge.json"
        if unified_path.exists():
            try:
                unified_data = json.loads(unified_path.read_text(encoding="utf-8"))
                for idx, item in enumerate(unified_data):
                    unit = KnowledgeUnit.model_validate(item)
                    # Run secret scan on content
                    _, issues, is_clean = SecretScanner.scan_and_redact(unit.content, unit.source_path)
                    if not is_clean:
                        errors.append(f"Secret detected in KnowledgeUnit '{unit.id}' (index {idx})")

                    # Verify physical file existence and line range validity
                    if unit.source_path and not unit.source_path.startswith("canonical/"):
                        phys_file = self.workspace_root / unit.source_path
                        if not phys_file.exists():
                            errors.append(f"KnowledgeUnit '{unit.id}' references non-existent physical file: {unit.source_path}")
                        elif unit.line_start is not None and unit.line_end is not None:
                            if unit.line_start < 1:
                                errors.append(f"KnowledgeUnit '{unit.id}' has invalid line_start < 1 ({unit.line_start})")
                            if unit.line_end < unit.line_start:
                                errors.append(f"KnowledgeUnit '{unit.id}' has line_end ({unit.line_end}) < line_start ({unit.line_start})")
                            total_lines = len(phys_file.read_text(encoding="utf-8").splitlines())
                            if unit.line_end > total_lines:
                                errors.append(f"KnowledgeUnit '{unit.id}' line_end ({unit.line_end}) exceeds physical file lines ({total_lines}) in {unit.source_path}")
            except Exception as exc:
                errors.append(f"Failed to parse unified_knowledge.json: {exc}")

        # Validate QA report
        qa_report_path = self.knowledge_dir / "qa" / "latest_report.json"
        if qa_report_path.exists():
            try:
                qa_data = json.loads(qa_report_path.read_text(encoding="utf-8"))
                report = QAReport.model_validate(qa_data)
                if not report.secret_scan_clean:
                    errors.append("QA Report indicates secret scan failure.")
            except Exception as exc:
                errors.append(f"Failed to parse latest_report.json: {exc}")

        is_valid = len(errors) == 0
        return is_valid, errors


def main() -> int:
    """CLI runner for standalone knowledge validation."""
    validator = KnowledgeValidator()
    is_valid, errors = validator.validate()

    if is_valid:
        print("[PASS] Knowledge base validation successful: all datasets verified and clean.")
        return 0
    else:
        print("[FAIL] Knowledge base validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
