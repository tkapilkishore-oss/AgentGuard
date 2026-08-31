"""Unit tests for provenance and physical source invariants."""

import json
from pathlib import Path

import pytest
from backend.app.knowledge.models import KnowledgeUnit, SourceTier


@pytest.fixture
def workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def unified_units(workspace_root: Path) -> list[KnowledgeUnit]:
    unified_file = workspace_root / "knowledge" / "generated" / "unified_knowledge.json"
    assert unified_file.exists(), "knowledge/generated/unified_knowledge.json must exist"
    data = json.loads(unified_file.read_text(encoding="utf-8"))
    return [KnowledgeUnit.model_validate(item) for item in data]


def test_all_source_paths_exist_on_disk(workspace_root: Path, unified_units: list[KnowledgeUnit]) -> None:
    """Invariant: Every source_path in knowledge base must resolve to a real file."""
    for u in unified_units:
        if u.source_path and not u.source_path.startswith("canonical/"):
            phys_file = workspace_root / u.source_path
            assert phys_file.exists(), f"Unit '{u.id}' references non-existent physical file: {u.source_path}"


def test_all_line_ranges_within_physical_file_bounds(workspace_root: Path, unified_units: list[KnowledgeUnit]) -> None:
    """Invariant: Every line range must satisfy 1 <= line_start <= line_end <= physical_file_lines."""
    for u in unified_units:
        if u.source_path and not u.source_path.startswith("canonical/"):
            phys_file = workspace_root / u.source_path
            if phys_file.exists() and u.line_start is not None and u.line_end is not None:
                assert u.line_start >= 1, f"Unit '{u.id}' has invalid line_start < 1 ({u.line_start})"
                assert u.line_end >= u.line_start, f"Unit '{u.id}' has line_end ({u.line_end}) < line_start ({u.line_start})"
                total_lines = len(phys_file.read_text(encoding="utf-8").splitlines())
                assert u.line_end <= total_lines, (
                    f"Unit '{u.id}' line_end ({u.line_end}) exceeds physical file lines ({total_lines}) in {u.source_path}"
                )


def test_health_endpoint_line_range_accurate(workspace_root: Path, unified_units: list[KnowledgeUnit]) -> None:
    """Specific test for GET /health endpoint line range in backend/app/main.py."""
    main_py = workspace_root / "backend" / "app" / "main.py"
    total_lines = len(main_py.read_text(encoding="utf-8").splitlines())

    health_units = [u for u in unified_units if u.route == "/health"]
    assert len(health_units) > 0, "GET /health unit must exist in knowledge base"
    for hu in health_units:
        assert hu.line_start is not None and hu.line_end is not None
        assert hu.line_end <= total_lines, f"GET /health line_end ({hu.line_end}) exceeds main.py line count ({total_lines})"


def test_no_phantom_claim_diff_viewer(unified_units: list[KnowledgeUnit]) -> None:
    """Invariant: ClaimDiffViewer must never appear in any knowledge unit symbol or title."""
    for u in unified_units:
        assert "ClaimDiffViewer" not in (u.symbol or ""), f"Phantom symbol found in unit '{u.id}'"
        assert "ClaimDiffViewer" not in u.title, f"Phantom symbol found in unit title '{u.title}'"
        assert "ClaimDiffViewer" not in u.source_path, f"Phantom path found in unit '{u.source_path}'"


def test_canonical_fact_tiers_accurate(unified_units: list[KnowledgeUnit]) -> None:
    """Invariant: Markdown-derived canonical facts must have TIER_5_SPEC_DOCS."""
    for u in unified_units:
        if u.id in ("fact_asymmetric_trust_architecture", "fact_trust_boundary_separation"):
            assert u.source_tier == SourceTier.TIER_5_SPEC_DOCS, (
                f"Fact '{u.id}' must be TIER_5_SPEC_DOCS, got {u.source_tier}"
            )
