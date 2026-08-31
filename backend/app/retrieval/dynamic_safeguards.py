"""Dynamic Data Safeguard — Enforces Hard Stop for Live State Queries."""

from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.models import (
    DynamicLiveAction,
    QueryClassification,
    RetrievalResult,
    RetrievalScoreBreakdown,
)


class DynamicDataSafeguard:
    """Enforces the hard security invariant that dynamic runtime values must not be fabricated."""

    @staticmethod
    def create_live_required_result(
        classification: QueryClassification,
    ) -> RetrievalResult | None:
        """Generates the authoritative LIVE_QUERY_REQUIRED sentinel result for dynamic queries."""
        if not classification.is_dynamic_live or not classification.dynamic_action:
            return None

        action: DynamicLiveAction = classification.dynamic_action
        if action.target_resource == "mandate_budget":
            domain = DomainCategory.K_BUDGETS
        elif action.target_resource == "audit_chain":
            domain = DomainCategory.P_AUDIT_TRAIL
        elif action.target_resource == "system_health":
            domain = DomainCategory.G_BACKEND_ARCHITECTURE
        elif action.target_resource == "product_stock":
            domain = DomainCategory.G_BACKEND_ARCHITECTURE
        else:
            domain = DomainCategory.L_TRANSACTIONS

        content = (
            f"[LIVE_QUERY_REQUIRED] Target runtime resource: '{action.target_resource}'.\n"
            f"Required backend tool/endpoint: '{action.required_endpoint}'.\n"
            f"Safeguard reason: {action.reason}\n"
            f"Static knowledge notice: Runtime state must be queried dynamically via the active backend API. "
            f"Static knowledge units explain schema and mechanics, but must NEVER be used as current values."
        )

        return RetrievalResult(
            knowledge_unit_id=f"dynamic_live_safeguard_{action.target_resource}",
            title=f"LIVE QUERY REQUIRED: {action.target_resource.replace('_', ' ').title()}",
            content=content,
            summary=f"Live tool query required via {action.required_endpoint} for {action.target_resource}.",
            domain=domain,
            source_tier=SourceTier.TIER_1_LIVE_TOOL,
            authority=AuthorityType.DYNAMIC_LIVE_REQUIRED,
            source_type="DYNAMIC_SAFEGUARD",
            source_path="backend/app/retrieval/dynamic_safeguards.py",
            line_start=1,
            line_end=50,
            symbol=action.target_resource,
            route=action.required_endpoint,
            frontend_action=None,
            score=1.0,
            retrieval_method="DYNAMIC_SAFEGUARD",
            dynamic_live_required=True,
            dynamic_tool_fallback=action.required_endpoint,
            tags=["dynamic_live_required", action.target_resource, "safeguard"],
            content_sha256="live_sentinel_hard_stop",
            selection_reason=(
                f"Hard dynamic data invariant: Query requested live state for '{action.target_resource}'. "
                f"Emitted LIVE_QUERY_REQUIRED requiring tool '{action.required_endpoint}'."
            ),
            score_breakdown=RetrievalScoreBreakdown(
                authority_score=1.0,
                query_alignment_bonus=0.5,
                total_score=1.0,
            ),
        )

    @staticmethod
    def sanitize_dynamic_results(
        results: list[RetrievalResult],
        is_dynamic: bool,
    ) -> list[RetrievalResult]:
        """Ensures that for dynamic queries, static units are labeled as explanatory context only."""
        if not is_dynamic:
            return results

        sanitized: list[RetrievalResult] = []
        for r in results:
            if r.dynamic_live_required and r.retrieval_method == "DYNAMIC_SAFEGUARD":
                sanitized.append(r)
            else:
                # Retain static knowledge as explanatory provenance with explicit notice
                r_copy = r.model_copy(deep=True)
                r_copy.selection_reason = (
                    f"Explanatory static architecture context only (Current value must be fetched via live tool). "
                    f"Original reason: {r.selection_reason}"
                )
                sanitized.append(r_copy)

        return sanitized
