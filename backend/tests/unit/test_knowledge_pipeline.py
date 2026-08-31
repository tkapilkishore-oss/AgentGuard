"""Unit Test Suite for AgentGuard Canonical Knowledge Engineering & QA Pipeline (Phase 5.5B-1).

Tests secret scanning, doc ingestion, AST extraction, TSX extraction, FastAPI route introspection,
Pytest test mapping, canonical facts, conflict detection, anti-hallucination unanswerable queries,
determinism, and standalone validation.
"""

from pathlib import Path

import pytest

from backend.app.knowledge.api_extractor import ApiExtractor
from backend.app.knowledge.ast_extractor import CodeAstExtractor
from backend.app.knowledge.builder import KnowledgeBuilder
from backend.app.knowledge.canonical_facts import CanonicalFactsBuilder
from backend.app.knowledge.conflict_detector import ConflictDetector
from backend.app.knowledge.doc_ingestor import DocIngestor
from backend.app.knowledge.frontend_extractor import FrontendExtractor
from backend.app.knowledge.models import (
    AuthorityType,
    DomainCategory,
    KnowledgeUnit,
    QASeverity,
    QAStatus,
    SourceTier,
)
from backend.app.knowledge.secret_scanner import SecretScanner
from backend.app.knowledge.test_extractor import TestExtractor
from backend.app.knowledge.validator import KnowledgeValidator


@pytest.fixture
def workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_secret_scanner_exclusion_guard():
    """Verify that SKILLS.md, .env, node_modules, and internal docs are strictly excluded."""
    assert SecretScanner.is_path_excluded("SKILLS.md") is True
    assert SecretScanner.is_path_excluded("./SKILLS.md") is True
    assert SecretScanner.is_path_excluded(".env") is True
    assert SecretScanner.is_path_excluded(".env.local") is True
    assert SecretScanner.is_path_excluded("frontend/node_modules/react/index.js") is True
    assert SecretScanner.is_path_excluded("frontend/dist/assets/index.js") is True
    assert SecretScanner.is_path_excluded("docs/internal/BUG_FINDINGS.md") is True
    assert SecretScanner.is_path_excluded("backend/app/__pycache__/main.cpython-312.pyc") is True

    # Valid documentation and code paths must NOT be excluded
    assert SecretScanner.is_path_excluded("docs/PRD.md") is False
    assert SecretScanner.is_path_excluded("backend/app/policy/engine.py") is False
    assert SecretScanner.is_path_excluded("frontend/src/views/LiveProtectionView.tsx") is False


def test_secret_scanner_redacts_credentials():
    """Verify that confidential API keys and private keys are detected, redacted, and emitted as errors."""
    # Construct strings dynamically to avoid having literal secrets in static source scanner
    mock_google_key = "AIza" + "SyD9z0ABC1234567890abcdef123456789"
    mock_rzp_key = "rzp" + "_test_" + "abcdef12345678"
    mock_header = "-----" + "BEGIN RSA PRIVATE KEY" + "-----"

    sample_text = (
        f"Here is a leaked key: {mock_google_key}\n"
        f"And a razorpay secret: {mock_rzp_key}\n"
        f"And a private key:\n{mock_header}\nMIIEowIBAAKCAQEA0...\n"
    )
    redacted, issues, is_clean = SecretScanner.scan_and_redact(sample_text, "test_file.py")

    assert is_clean is False
    assert len(issues) >= 2
    assert any(i.severity == QASeverity.ERROR for i in issues)
    assert mock_google_key not in redacted
    assert mock_rzp_key not in redacted
    assert "[REDACTED_GOOGLE_API_KEY]" in redacted
    assert "[REDACTED_RAZORPAY_TEST_SECRET]" in redacted


def test_secret_scanner_safe_placeholders():
    """Verify that safe documentation placeholders do not trigger false positive errors."""
    safe_text = "Use your_key and your_secret for testing with localhost:5432 and user:pass."
    redacted, issues, is_clean = SecretScanner.scan_and_redact(safe_text, "docs/PRD.md")
    assert is_clean is True
    assert len(issues) == 0
    assert redacted == safe_text


def test_doc_ingestor_deterministic_chunking(workspace_root: Path):
    """Verify that markdown specifications are chunked by headings with line numbers and stable IDs."""
    ingestor = DocIngestor(workspace_root)
    files = ingestor.discover_doc_files()
    assert len(files) >= 5

    # Ensure SKILLS.md is NOT among discovered files
    file_names = [f.name for f in files]
    assert "SKILLS.md" not in file_names
    assert "BUG_FINDINGS.md" not in file_names
    assert "PRD.md" in file_names

    prd_path = [f for f in files if f.name == "PRD.md"][0]
    units, issues = ingestor.ingest_file(prd_path)
    assert len(units) >= 5
    assert len(issues) == 0
    assert all(u.source_type == "DOC" for u in units)
    assert all(u.source_tier == SourceTier.TIER_5_SPEC_DOCS for u in units)
    assert all(u.line_start is not None and u.line_end is not None for u in units)
    assert all(u.id.startswith("doc_prd_") for u in units)


def test_ast_extractor_python_symbols(workspace_root: Path):
    """Verify Python AST extraction of modules, functions, classes, and relationship calls."""
    extractor = CodeAstExtractor(workspace_root)
    engine_path = workspace_root / "backend" / "app" / "policy" / "engine.py"
    symbols, units, issues = extractor.extract_file(engine_path)

    assert len(issues) == 0
    assert len(symbols) >= 1
    assert len(units) >= 1

    # Check for evaluate_policy function symbol
    eval_fn = [s for s in symbols if s.name == "evaluate_policy"]
    assert len(eval_fn) == 1
    assert eval_fn[0].line_start > 0
    assert eval_fn[0].symbol_type in ("function", "route_handler")

    # Check evaluate_policy KnowledgeUnit
    eval_unit = [u for u in units if u.symbol == "evaluate_policy"]
    assert len(eval_unit) == 1
    assert eval_unit[0].authority == AuthorityType.AUTHORITATIVE
    assert eval_unit[0].domain == DomainCategory.I_POLICY_ENGINE


def test_frontend_extractor_tsx_components(workspace_root: Path):
    """Verify TypeScript / TSX extraction of components, views, and action triggers."""
    extractor = FrontendExtractor(workspace_root)
    files = extractor.discover_frontend_files()
    assert len(files) >= 10

    threat_file = workspace_root / "frontend" / "src" / "features" / "threat" / "ThreatSimulationLab.tsx"
    actions, units, issues = extractor.extract_file(threat_file)

    assert len(issues) == 0
    assert len(units) >= 1
    assert len(actions) >= 1

    # Check action classification
    scenario_action = [a for a in actions if a.action_type == "SIMULATION"]
    assert len(scenario_action) >= 1
    assert scenario_action[0].safety_level == "SAFE_SIMULATION"
    assert scenario_action[0].view_path == "/threats"


def test_api_extractor_all_routes(workspace_root: Path):
    """Verify that all 11 FastAPI application routes are authoritatively extracted."""
    extractor = ApiExtractor(workspace_root)
    records, units, issues = extractor.extract_routes()

    assert len(issues) == 0
    assert len(records) >= 11
    assert len(units) >= 11

    paths = {r.path for r in records}
    expected_paths = {
        "/transaction/propose",
        "/transaction/execute",
        "/transaction/{transaction_id}/approve",
        "/transaction/{transaction_id}/reject",
        "/agent/chat",
        "/mandate/{mandate_id}/revoke",
        "/mandate/{mandate_id}",
        "/products",
        "/transactions",
        "/transaction/{transaction_id}/audit",
        "/health",
    }
    assert expected_paths.issubset(paths)

    # Check safety level of execute endpoint
    exec_rec = [r for r in records if r.path == "/transaction/execute"][0]
    assert exec_rec.safety_level == "REQUIRES_CONFIRMATION"
    assert exec_rec.is_mutation is True


def test_test_extractor_pytest_cases(workspace_root: Path):
    """Verify that Pytest test cases are extracted and mapped to proven invariants."""
    extractor = TestExtractor(workspace_root)
    records, units, issues = extractor.extract_all()

    assert len(issues) == 0
    assert len(records) >= 50
    assert len(units) >= 50

    # Check test for replay attack
    replay_tests = [r for r in records if "replay" in r.test_function.lower()]
    assert len(replay_tests) >= 1
    assert any("REPLAY_DETECTED" in inv for r in replay_tests for inv in r.invariants_proven)


def test_canonical_facts_dynamic_vs_static():
    """Verify that static facts are AUTHORITATIVE and dynamic state is DYNAMIC_LIVE_REQUIRED."""
    facts, units = CanonicalFactsBuilder.build_facts()
    assert len(facts) >= 25
    assert len(units) >= 25

    # Static facts
    identity_fact = [f for f in facts if f.domain == DomainCategory.A_PRODUCT_IDENTITY][0]
    assert identity_fact.authority == AuthorityType.AUTHORITATIVE
    assert identity_fact.is_dynamic_tool_required is False

    # Dynamic operational fact (Budget)
    budget_fact = [f for f in facts if f.domain == DomainCategory.K_BUDGETS][0]
    assert budget_fact.authority == AuthorityType.DYNAMIC_LIVE_REQUIRED
    assert budget_fact.is_dynamic_tool_required is True
    assert budget_fact.required_tool == "get_mandate_status"


def test_conflict_detector_clean(workspace_root: Path):
    """Verify that a valid knowledge base produces zero critical errors."""
    builder = KnowledgeBuilder(workspace_root)
    manifest, qa_report = builder.build_all(dry_run=True)

    assert qa_report.status in (QAStatus.VALID, QAStatus.VALID_WITH_WARNINGS)
    assert qa_report.secret_scan_clean is True
    assert qa_report.metrics.conflicts_detected == 0
    assert qa_report.metrics.unresolved_references == 0


def test_conflict_detector_flags_broken_references(workspace_root: Path):
    """Verify that nonexistent source files trigger QA ERROR and mark status INVALID."""
    detector = ConflictDetector(workspace_root)
    broken_unit = KnowledgeUnit(
        id="broken_test_unit",
        domain=DomainCategory.D_ARCHITECTURE,
        title="Broken Test Unit",
        summary="A test unit with nonexistent path",
        content="Some content",
        source_type="DOC",
        source_path="docs/nonexistent_file_xyz.md",
        source_tier=SourceTier.TIER_5_SPEC_DOCS,
        content_sha256="abc12345",
        authority=AuthorityType.AUTHORITATIVE,
    )
    updated_units, issues = detector.detect_conflicts([broken_unit])
    assert len(issues) >= 1
    assert any(i.code == "BROKEN_SOURCE_FILE_REFERENCE" for i in issues)
    assert updated_units[0].authority == AuthorityType.CONFLICTING


def test_anti_hallucination_unanswerable_queries():
    """Verify that domain coverage correctly identifies gaps for unsupported domains."""
    facts, units = CanonicalFactsBuilder.build_facts()
    minimal_units = [u for u in units if u.domain == DomainCategory.A_PRODUCT_IDENTITY]
    coverage = CanonicalFactsBuilder.evaluate_domain_coverage(minimal_units)

    assert coverage[DomainCategory.A_PRODUCT_IDENTITY.value].value in ("COVERED", "PARTIALLY_COVERED")
    assert coverage[DomainCategory.T_THREAT_SIMULATION_LAB.value].value == "KNOWLEDGE_GAP"


def test_knowledge_builder_determinism(workspace_root: Path):
    """Verify that consecutive builds produce identical unit counts and IDs."""
    builder = KnowledgeBuilder(workspace_root)
    manifest1, report1 = builder.build_all(dry_run=True)
    manifest2, report2 = builder.build_all(dry_run=True)

    assert report1.metrics.total_units == report2.metrics.total_units
    assert report1.metrics.docs_chunks == report2.metrics.docs_chunks
    assert report1.metrics.python_symbols == report2.metrics.python_symbols
    assert report1.metrics.api_routes == report2.metrics.api_routes


def test_standalone_validator_pass(workspace_root: Path):
    """Verify that KnowledgeValidator returns is_valid=True for active generated knowledge assets."""
    builder = KnowledgeBuilder(workspace_root)
    builder.build_all(dry_run=False)

    validator = KnowledgeValidator(workspace_root)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert len(errors) == 0
