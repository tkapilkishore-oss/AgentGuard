"""Documentation Ingestion Module for AgentGuard Knowledge Pipeline.

Parses markdown specifications, preserves heading structure and line ranges,
computes deterministic fingerprints, and enforces secret safety.
"""

import hashlib
from pathlib import Path

from backend.app.knowledge.models import (
    AuthorityType,
    DomainCategory,
    FreshnessStatus,
    KnowledgeUnit,
    QAIssue,
    SourceTier,
)
from backend.app.knowledge.secret_scanner import SecretScanner

# Mapping of documentation filenames to primary Domain Categories
DOC_DOMAIN_MAPPING: dict[str, DomainCategory] = {
    "PRD.md": DomainCategory.A_PRODUCT_IDENTITY,
    "TRD.md": DomainCategory.G_BACKEND_ARCHITECTURE,
    "Architecture.md": DomainCategory.D_ARCHITECTURE,
    "threat_model.md": DomainCategory.E_TRUST_MODEL,
    "test_plan.md": DomainCategory.Y_TEST_SUITES,
    "seed_data.md": DomainCategory.O_ATTACK_SCENARIOS,
    "conventions.md": DomainCategory.Z_DESIGN_DECISIONS,
    "phase0_corrections.md": DomainCategory.F_SECURITY_INVARIANTS,
    "AGENTS.md": DomainCategory.N_AGENT_BEHAVIOR,
    "README.md": DomainCategory.A_PRODUCT_IDENTITY,
}


class DocIngestor:
    """Ingests, chunks, and fingerprints documentation files into KnowledgeUnits."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def discover_doc_files(self) -> list[Path]:
        """Finds all valid specification markdown files, excluding protected/ignored paths."""
        docs_dir = self.workspace_root / "docs"
        candidate_files: list[Path] = []

        if docs_dir.exists():
            for p in sorted(docs_dir.glob("*.md")):
                rel = p.relative_to(self.workspace_root)
                if not SecretScanner.is_path_excluded(rel):
                    candidate_files.append(p)

        readme = self.workspace_root / "README.md"
        if readme.exists() and not SecretScanner.is_path_excluded(readme.relative_to(self.workspace_root)):
            candidate_files.append(readme)

        return candidate_files

    def ingest_file(self, file_path: Path) -> tuple[list[KnowledgeUnit], list[QAIssue]]:
        """Parses a single markdown documentation file into heading-structured KnowledgeUnits."""
        rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
        issues: list[QAIssue] = []

        # Check exclusion guard
        if SecretScanner.is_path_excluded(rel_path):
            return [], issues

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="FILE_READ_ERROR",
                    message=f"Failed to read file {rel_path}: {exc}",
                    source_path=rel_path,
                )
            )
            return [], issues

        # Pre-ingestion secret scan & redaction
        clean_text, scan_issues, is_clean = SecretScanner.scan_and_redact(raw_text, rel_path)
        issues.extend(scan_issues)

        # Determine domain for document
        base_name = file_path.name
        primary_domain = DOC_DOMAIN_MAPPING.get(base_name, DomainCategory.D_ARCHITECTURE)

        # Parse sections based on markdown headings
        lines = clean_text.splitlines()
        units: list[KnowledgeUnit] = []

        current_heading = base_name.replace(".md", "")
        current_lines: list[str] = []
        start_line = 1

        for idx, line in enumerate(lines, start=1):
            if line.startswith("#"):
                # Flush previous section if non-empty
                if current_lines and "\n".join(current_lines).strip():
                    section_content = "\n".join(current_lines).strip()
                    unit = self._create_unit(
                        rel_path=rel_path,
                        heading=current_heading,
                        content=section_content,
                        domain=primary_domain,
                        line_start=start_line,
                        line_end=idx - 1,
                    )
                    units.append(unit)

                current_heading = line.lstrip("#").strip()
                current_lines = [line]
                start_line = idx
            else:
                current_lines.append(line)

        # Flush final section
        if current_lines and "\n".join(current_lines).strip():
            section_content = "\n".join(current_lines).strip()
            unit = self._create_unit(
                rel_path=rel_path,
                heading=current_heading,
                content=section_content,
                domain=primary_domain,
                line_start=start_line,
                line_end=len(lines),
            )
            units.append(unit)

        return units, issues

    def _create_unit(
        self,
        rel_path: str,
        heading: str,
        content: str,
        domain: DomainCategory,
        line_start: int,
        line_end: int,
    ) -> KnowledgeUnit:
        """Constructs a deterministic KnowledgeUnit."""
        # Compute deterministic content SHA-256
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Deterministic stable ID: doc_{file_stem}_{slug}_{hash[:8]}
        file_stem = Path(rel_path).stem.lower().replace("-", "_")
        heading_slug = "".join(c if c.isalnum() else "_" for c in heading.lower())[:24].strip("_")
        unit_id = f"doc_{file_stem}_{heading_slug}_{content_hash[:8]}"

        # First non-empty paragraph as summary
        summary = ""
        for p in content.split("\n\n"):
            clean_p = p.strip()
            if clean_p and not clean_p.startswith("#"):
                summary = clean_p[:200]
                break
        if not summary:
            summary = heading

        return KnowledgeUnit(
            id=unit_id,
            domain=domain,
            title=f"{Path(rel_path).name}: {heading}",
            summary=summary,
            content=content,
            source_type="DOC",
            source_path=rel_path,
            source_tier=SourceTier.TIER_5_SPEC_DOCS,
            line_start=line_start,
            line_end=line_end,
            symbol=None,
            route=None,
            content_sha256=content_hash,
            authority=AuthorityType.HISTORICAL,
            freshness=FreshnessStatus.VERIFIED,
            relationships=[],
            tags=[domain.value.lower(), file_stem],
        )

    def ingest_all(self) -> tuple[list[KnowledgeUnit], list[QAIssue]]:
        """Discovers and ingests all valid documentation files."""
        files = self.discover_doc_files()
        all_units: list[KnowledgeUnit] = []
        all_issues: list[QAIssue] = []

        for f in files:
            units, issues = self.ingest_file(f)
            all_units.extend(units)
            all_issues.extend(issues)

        return all_units, all_issues
