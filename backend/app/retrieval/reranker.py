"""Authority-Aware Reranker Enforcing Constrained Deterministic Precedence."""

from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.models import (
    QueryCategory,
    QueryClassification,
    RetrievalResult,
    RetrievalScoreBreakdown,
    ScoringWeights,
)


class AuthorityReranker:
    """Reranks candidate results combining exact, lexical, semantic, domain, and authority tiers.

    Enforces constrained authority precedence:
    LIVE_TOOL (1.0) > SOURCE_CODE (0.95) > API_SCHEMA (0.90) > TESTS (0.85) > SPEC_DOCS (0.75) > HISTORICAL (0.50).
    Prevents semantic similarity from overriding higher-authority executable code evidence.
    """

    TIER_WEIGHTS: dict[SourceTier, float] = {
        SourceTier.TIER_1_LIVE_TOOL: 1.00,
        SourceTier.TIER_2_SOURCE_CODE: 0.95,
        SourceTier.TIER_3_API_SCHEMA: 0.90,
        SourceTier.TIER_4_AUTOMATED_TESTS: 0.85,
        SourceTier.TIER_5_SPEC_DOCS: 0.75,
        SourceTier.TIER_6_HISTORICAL: 0.50,
    }

    AUTHORITY_TYPE_WEIGHTS: dict[AuthorityType, float] = {
        AuthorityType.DYNAMIC_LIVE_REQUIRED: 1.00,
        AuthorityType.AUTHORITATIVE: 0.95,
        AuthorityType.SOURCE_DERIVED: 0.85,
        AuthorityType.HISTORICAL: 0.60,
        AuthorityType.CONFLICTING: 0.40,
        AuthorityType.UNKNOWN: 0.20,
    }

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights(
            w_exact=0.35,
            w_lexical=0.25,
            w_semantic=0.15,
            w_authority=0.15,
            w_domain=0.25,
            bonus_alignment=0.20,
        )

    def rerank(
        self,
        candidates: list[RetrievalResult],
        classification: QueryClassification,
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Performs multi-signal deterministic scoring with authority constraints."""
        if not candidates:
            return []

        # Deduplicate candidates by knowledge_unit_id, accumulating signals
        merged: dict[str, RetrievalResult] = {}
        for c in candidates:
            if c.knowledge_unit_id not in merged:
                merged[c.knowledge_unit_id] = c
            else:
                existing = merged[c.knowledge_unit_id]
                # Merge score breakdowns
                existing.score_breakdown.exact_score = max(
                    existing.score_breakdown.exact_score, c.score_breakdown.exact_score
                )
                existing.score_breakdown.lexical_bm25_score = max(
                    existing.score_breakdown.lexical_bm25_score, c.score_breakdown.lexical_bm25_score
                )
                existing.score_breakdown.semantic_score = max(
                    existing.score_breakdown.semantic_score, c.score_breakdown.semantic_score
                )

        scored_results: list[RetrievalResult] = []

        for unit_id, item in merged.items():
            breakdown = item.score_breakdown

            # 1. Base Signal Scores
            s_exact = breakdown.exact_score
            s_lexical = breakdown.lexical_bm25_score
            s_semantic = breakdown.semantic_score

            # 2. Domain Match Bonus
            s_domain = 0.0
            if item.domain in classification.domain_hints:
                s_domain = 1.0
            breakdown.domain_bonus = s_domain

            # 3. Source Tier & Authority Weights
            tier_val = self.TIER_WEIGHTS.get(item.source_tier, 0.70)
            auth_val = self.AUTHORITY_TYPE_WEIGHTS.get(item.authority, 0.70)
            breakdown.source_tier_score = tier_val
            breakdown.authority_score = auth_val

            # 4. Query Alignment Bonus
            align_bonus = 0.0
            if classification.category == QueryCategory.CODE_SYMBOL and item.source_tier in (
                SourceTier.TIER_2_SOURCE_CODE,
                SourceTier.TIER_3_API_SCHEMA,
            ):
                align_bonus += self.weights.bonus_alignment
                # Specificity bonus: Concrete functions and classes outrank bare module files
                if item.symbol and any(s.lower() in item.symbol.lower() for s in classification.extracted_symbols):
                    if not item.title.startswith("Module:"):
                        align_bonus += 0.25
                elif item.title.startswith("Module:"):
                    align_bonus -= 0.15

                # Disambiguate policy vs retrieval engine
                if DomainCategory.I_POLICY_ENGINE in classification.domain_hints or any(
                    s in ["PolicyEngine", "verify_proposal", "evaluate_policy"] for s in classification.extracted_symbols
                ):
                    if "backend/app/policy/" in item.source_path:
                        align_bonus += 0.35
                    elif "backend/app/retrieval/" in item.source_path:
                        align_bonus -= 0.30
                elif "RetrievalEngine" in classification.extracted_symbols or "backend/app/retrieval/" in item.source_path:
                    if "backend/app/retrieval/" in item.source_path:
                        align_bonus += 0.35

            elif classification.category == QueryCategory.API_ROUTE and (
                item.source_tier == SourceTier.TIER_3_API_SCHEMA or item.source_type == "API_ROUTE"
            ):
                align_bonus += self.weights.bonus_alignment
            elif classification.category == QueryCategory.TEST_VERIFICATION and (
                item.source_tier == SourceTier.TIER_4_AUTOMATED_TESTS or item.source_type == "PYTEST"
            ):
                align_bonus += self.weights.bonus_alignment
            elif classification.category == QueryCategory.FRONTEND_ACTION:
                if item.source_type == "TSX_COMPONENT" or "frontend/src/" in item.source_path:
                    align_bonus += self.weights.bonus_alignment
                    if any(c.lower() in item.title.lower() or c.lower() in item.source_path.lower() for c in classification.extracted_components):
                        align_bonus += 0.30
                elif item.source_tier in (SourceTier.TIER_5_SPEC_DOCS, SourceTier.TIER_6_HISTORICAL):
                    align_bonus -= 0.20
            elif classification.category == QueryCategory.DYNAMIC_LIVE_DATA and item.authority == AuthorityType.DYNAMIC_LIVE_REQUIRED:
                align_bonus += 0.50

            # Boost exact matches
            exact_boost = 0.15 if s_exact >= 0.9 else 0.0
            breakdown.query_alignment_bonus = align_bonus + exact_boost

            # 5. Hybrid Composite Score
            relevance = (
                self.weights.w_exact * s_exact
                + self.weights.w_lexical * s_lexical
                + self.weights.w_semantic * s_semantic
                + self.weights.w_domain * s_domain
                + align_bonus
                + exact_boost
            )

            # 6. Constrained Authority Scaling (Prevents weak docs from overtaking code)
            composite_score = relevance * (0.6 + 0.4 * (tier_val * auth_val))

            # If dynamic live query and sentinel, guarantee top score
            if item.dynamic_live_required and item.retrieval_method == "DYNAMIC_SAFEGUARD":
                composite_score = 1.0

            breakdown.total_score = round(composite_score, 4)
            item.score = breakdown.total_score

            # Build transparent selection reason
            reasons = []
            if s_exact > 0:
                reasons.append(f"exact={s_exact:.2f}")
            if s_lexical > 0:
                reasons.append(f"lexical={s_lexical:.2f}")
            if s_semantic > 0:
                reasons.append(f"semantic={s_semantic:.2f}")
            if s_domain > 0:
                reasons.append("domain_hint")
            reasons.append(f"tier={item.source_tier.value}")
            reasons.append(f"auth={item.authority.value}")

            item.selection_reason = (
                f"Selected via [{item.retrieval_method}] (Score: {composite_score:.4f}; "
                f"Components: {', '.join(reasons)})"
            )

            scored_results.append(item)

        # Sort deterministically by score descending, then tier priority, then unit ID ascending
        scored_results.sort(
            key=lambda r: (
                r.score,
                self.TIER_WEIGHTS.get(r.source_tier, 0.0),
                -len(r.knowledge_unit_id),
                r.knowledge_unit_id,
            ),
            reverse=True,
        )

        return scored_results[:top_k]
