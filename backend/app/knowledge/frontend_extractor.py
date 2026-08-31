"""TypeScript / TSX Frontend Knowledge Extractor for AgentGuard Knowledge Pipeline.

Extracts views, components, action buttons, API client dependencies, and safety levels
from the active React/Vite/Tailwind frontend source tree.
"""

import hashlib
import re
from pathlib import Path

from backend.app.knowledge.models import (
    AuthorityType,
    CodeRelationship,
    DomainCategory,
    FreshnessStatus,
    FrontendActionRecord,
    KnowledgeUnit,
    QAIssue,
    SourceTier,
)
from backend.app.knowledge.secret_scanner import SecretScanner

VIEW_DOMAIN_MAPPING: dict[str, DomainCategory] = {
    "HomeView.tsx": DomainCategory.R_FRONTEND_ARCHITECTURE,
    "LiveProtectionView.tsx": DomainCategory.U_LIVE_PROTECTION,
    "ThreatLabView.tsx": DomainCategory.T_THREAT_SIMULATION_LAB,
    "ForensicLedgerView.tsx": DomainCategory.V_FORENSIC_LEDGER,
    "SecurityCockpitHeader.tsx": DomainCategory.S_NAVIGATION,
    "DeveloperWireDrawer.tsx": DomainCategory.W_DEVELOPER_WIRE_TELEMETRY,
    "ConversationalVoiceDrawer.tsx": DomainCategory.X_CONVERSATIONAL_INTERFACE,
    "FirewallInspectionHero.tsx": DomainCategory.U_LIVE_PROTECTION,
    "UntrustedClientChamber.tsx": DomainCategory.N_AGENT_BEHAVIOR,
    "ThreatSimulationLab.tsx": DomainCategory.T_THREAT_SIMULATION_LAB,
    "ForensicLedger.tsx": DomainCategory.V_FORENSIC_LEDGER,
    "AgentGuardContext.tsx": DomainCategory.R_FRONTEND_ARCHITECTURE,
    "api.ts": DomainCategory.R_FRONTEND_ARCHITECTURE,
}


class FrontendExtractor:
    """Extracts frontend component metadata, interactive triggers, and API bindings."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def discover_frontend_files(self) -> list[Path]:
        """Discovers active TS/TSX source files in frontend/src, excluding dist and node_modules."""
        src_dir = self.workspace_root / "frontend" / "src"
        ts_files: list[Path] = []

        if src_dir.exists():
            for p in sorted(src_dir.rglob("*.tsx")):
                rel = p.relative_to(self.workspace_root)
                if not SecretScanner.is_path_excluded(rel):
                    ts_files.append(p)
            for p in sorted(src_dir.rglob("*.ts")):
                rel = p.relative_to(self.workspace_root)
                if not SecretScanner.is_path_excluded(rel) and not p.name.endswith(".d.ts"):
                    ts_files.append(p)

        return ts_files

    def extract_file(
        self, file_path: Path
    ) -> tuple[list[FrontendActionRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Extracts component definitions, UI actions, and API bindings from a TS/TSX file."""
        rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
        issues: list[QAIssue] = []
        actions: list[FrontendActionRecord] = []
        units: list[KnowledgeUnit] = []

        if SecretScanner.is_path_excluded(rel_path):
            return actions, units, issues

        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="TSX_FILE_READ_ERROR",
                    message=f"Failed to read {rel_path}: {exc}",
                    source_path=rel_path,
                )
            )
            return actions, units, issues

        clean_code, scan_issues, is_clean = SecretScanner.scan_and_redact(raw_content, rel_path)
        issues.extend(scan_issues)

        file_stem = file_path.name
        primary_domain = VIEW_DOMAIN_MAPPING.get(file_stem, DomainCategory.R_FRONTEND_ARCHITECTURE)
        content_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

        # Extract React component declarations
        component_matches = re.findall(
            r"export\s+const\s+([A-Za-z0-9_]+)\s*:\s*React\.FC", clean_code
        )
        if not component_matches:
            component_matches = re.findall(
                r"export\s+(?:function|const)\s+([A-Za-z0-9_]+)", clean_code
            )

        # Extract API calls (api.someMethod or /some/endpoint)
        api_calls = re.findall(r"api\.([A-Za-z0-9_]+)", clean_code)
        endpoint_calls = re.findall(r"fetchEnvelope<[^>]*>\(['\"]([^'\"]+)['\"]", clean_code)

        # Extract interactive button labels and handlers
        button_matches = re.findall(
            r"<button[^>]*onClick=\{([^}]+)\}[^>]*>(.*?)</button>", clean_code, re.DOTALL
        )

        comp_name = component_matches[0] if component_matches else file_path.stem
        comp_summary = f"React component/module `{comp_name}` located at `{rel_path}`."

        # Module-level Knowledge Unit
        relationships: list[CodeRelationship] = []
        for api_call in set(api_calls):
            relationships.append(
                CodeRelationship(
                    source_symbol=comp_name,
                    target_symbol=f"api.{api_call}",
                    relationship_type="CALLS_API_CLIENT",
                )
            )

        unit = KnowledgeUnit(
            id=f"fe_{file_path.stem.lower()}_{content_hash[:8]}",
            domain=primary_domain,
            title=f"UI Component: {comp_name} ({rel_path})",
            summary=comp_summary,
            content=(
                f"File: `{rel_path}`\n"
                f"Component: `{comp_name}`\n"
                f"Domain: {primary_domain.value}\n"
                f"API Client Methods Used: {', '.join(set(api_calls)) if api_calls else 'None'}\n"
                f"Direct Endpoints: {', '.join(set(endpoint_calls)) if endpoint_calls else 'None'}\n\n"
                f"Source Summary: Exports component `{comp_name}` with {len(button_matches)} interactive action triggers."
            ),
            source_type="TSX_COMPONENT",
            source_path=rel_path,
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            line_start=1,
            line_end=len(clean_code.splitlines()),
            symbol=comp_name,
            content_sha256=content_hash,
            authority=AuthorityType.AUTHORITATIVE,
            freshness=FreshnessStatus.VERIFIED,
            relationships=relationships,
            tags=["frontend", "react", "typescript", file_path.stem.lower(), primary_domain.value.lower()],
        )
        units.append(unit)

        # Extract structured actions for primary views
        extracted_actions = self._extract_specific_actions(comp_name, rel_path, clean_code)
        actions.extend(extracted_actions)

        return actions, units, issues

    def _extract_specific_actions(
        self, comp_name: str, rel_path: str, code: str
    ) -> list[FrontendActionRecord]:
        """Extracts high-value user-triggerable actions mapped to safety tiers."""
        records: list[FrontendActionRecord] = []

        if "ThreatSimulationLab" in comp_name:
            records.append(
                FrontendActionRecord(
                    id="action_threat_run_scenario",
                    view_name="ThreatLabView",
                    view_path="/threats",
                    component_name=comp_name,
                    action_label="Run Simulation Scenario (1-6)",
                    action_type="SIMULATION",
                    api_endpoint="/transaction/propose",
                    safety_level="SAFE_SIMULATION",
                    description="Executes one of the 6 deterministic threat simulation attacks.",
                )
            )
            records.append(
                FrontendActionRecord(
                    id="action_threat_custom_attack",
                    view_name="ThreatLabView",
                    view_path="/threats",
                    component_name=comp_name,
                    action_label="Inject Custom Claim to Firewall",
                    action_type="PROPOSAL",
                    api_endpoint="/transaction/propose",
                    safety_level="PROPOSE_ONLY",
                    description="Submits a custom claimed price and quantity proposal to the firewall.",
                )
            )
        elif "FirewallInspectionHero" in comp_name:
            records.append(
                FrontendActionRecord(
                    id="action_firewall_execute_payment",
                    view_name="LiveProtectionView",
                    view_path="/live",
                    component_name=comp_name,
                    action_label="Execute Payment via Razorpay Gateway",
                    action_type="EXECUTION",
                    api_endpoint="/transaction/execute",
                    safety_level="REQUIRES_USER_CONFIRMATION",
                    description="Dispatches authorized transaction for atomic budget reservation and Razorpay capture.",
                )
            )
            records.append(
                FrontendActionRecord(
                    id="action_firewall_approve_escalation",
                    view_name="LiveProtectionView",
                    view_path="/live",
                    component_name=comp_name,
                    action_label="Approve Over-Budget Purchase",
                    action_type="EXECUTION",
                    api_endpoint="/transaction/{id}/approve",
                    safety_level="SUPERVISOR_ONLY",
                    description="Human supervisor explicit authorization for an escalated purchase.",
                )
            )
            records.append(
                FrontendActionRecord(
                    id="action_firewall_reject_escalation",
                    view_name="LiveProtectionView",
                    view_path="/live",
                    component_name=comp_name,
                    action_label="Reject Proposal",
                    action_type="EXECUTION",
                    api_endpoint="/transaction/{id}/reject",
                    safety_level="SUPERVISOR_ONLY",
                    description="Human supervisor explicit denial of an escalated purchase.",
                )
            )
        elif "SecurityCockpitHeader" in comp_name:
            records.append(
                FrontendActionRecord(
                    id="action_cockpit_revoke_mandate",
                    view_name="GlobalCockpit",
                    view_path="/*",
                    component_name=comp_name,
                    action_label="Revoke Mandate",
                    action_type="EXECUTION",
                    api_endpoint="/mandate/{id}/revoke",
                    safety_level="REQUIRES_USER_CONFIRMATION",
                    description="Revokes the active spending mandate, preventing subsequent payments.",
                )
            )
            records.append(
                FrontendActionRecord(
                    id="action_cockpit_talk_to_assistant",
                    view_name="GlobalCockpit",
                    view_path="/*",
                    component_name=comp_name,
                    action_label="Talk to AgentGuard",
                    action_type="NAVIGATION",
                    api_endpoint=None,
                    safety_level="READ_ONLY",
                    description="Opens the Conversational Assistant voice & text drawer.",
                )
            )
        elif "ForensicLedger" in comp_name:
            records.append(
                FrontendActionRecord(
                    id="action_forensics_export_json",
                    view_name="ForensicLedgerView",
                    view_path="/forensics",
                    component_name=comp_name,
                    action_label="Export Evidence JSON",
                    action_type="INSPECTION",
                    api_endpoint="/transaction/{id}/audit",
                    safety_level="READ_ONLY",
                    description="Exports the complete chronological cryptographic SHA-256 audit trace as JSON.",
                )
            )

        return records

    def extract_all(
        self,
    ) -> tuple[list[FrontendActionRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Discovers and extracts all frontend TS/TSX component knowledge."""
        files = self.discover_frontend_files()
        all_actions: list[FrontendActionRecord] = []
        all_units: list[KnowledgeUnit] = []
        all_issues: list[QAIssue] = []

        for f in files:
            actions, units, issues = self.extract_file(f)
            all_actions.extend(actions)
            all_units.extend(units)
            all_issues.extend(issues)

        return all_actions, all_units, all_issues
