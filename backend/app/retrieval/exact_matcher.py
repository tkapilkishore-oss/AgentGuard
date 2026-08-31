"""Deterministic Exact Retrieval Index for Knowledge Units, Symbols, Routes, and Paths."""

from collections import defaultdict
from pathlib import Path

from backend.app.knowledge.models import KnowledgeUnit
from backend.app.retrieval.models import QueryClassification, RetrievalResult, RetrievalScoreBreakdown


class ExactMatcher:
    """Provides deterministic O(1) exact lookups across identifiers, symbols, routes, and paths."""

    def __init__(self, units: list[KnowledgeUnit]) -> None:
        self.units = units
        self.id_map: dict[str, KnowledgeUnit] = {}
        self.symbol_map: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.route_map: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.action_map: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.path_map: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.constant_map: dict[str, list[KnowledgeUnit]] = defaultdict(list)

        self._build_indices()

    def _build_indices(self) -> None:
        for unit in self.units:
            # 1. ID Index
            self.id_map[unit.id] = unit

            # 2. Symbol Index
            if unit.symbol:
                clean_sym = unit.symbol.strip()
                self.symbol_map[clean_sym.lower()].append(unit)
                # If qualified (e.g. PolicyEngine.verify_proposal), index both qualified and unqualified
                if "." in clean_sym:
                    unqual = clean_sym.split(".")[-1]
                    self.symbol_map[unqual.lower()].append(unit)

            # 3. Route Index
            if unit.route:
                clean_route = unit.route.strip()
                self.route_map[clean_route.lower()].append(unit)
                # Index path alone without method if present (e.g., "POST /transaction/propose" -> "/transaction/propose")
                parts = clean_route.split()
                if len(parts) == 2:
                    self.route_map[parts[1].lower()].append(unit)
                    self.route_map[f"{parts[0].lower()} {parts[1].lower()}"].append(unit)
                elif clean_route.startswith("/"):
                    # Index with common HTTP methods
                    for m in ["get", "post", "put", "delete"]:
                        self.route_map[f"{m} {clean_route.lower()}"].append(unit)

            # 4. Source Path and Basename Index
            if unit.source_path:
                clean_path = unit.source_path.strip().lower()
                self.path_map[clean_path].append(unit)
                basename = Path(unit.source_path).name.lower()
                self.path_map[basename].append(unit)

            # 5. Frontend Actions & Views (from tags or summary)
            for tag in unit.tags:
                tag_lower = tag.lower()
                self.constant_map[tag_lower].append(unit)

            # 6. Specific invariants & constants
            known_constants = [
                "price_mismatch",
                "merchant_mismatch",
                "budget_exceeded",
                "replay_detected",
                "mandate_revoked",
                "sha-256",
                "hash_chain",
                "idempotency",
                "gemini_api_key",
                "claim_diff",
                "execute payment",
                "threat simulation lab",
                "live protection",
                "forensic ledger",
                "wire telemetry",
            ]
            content_lower = unit.content.lower()
            title_lower = unit.title.lower()
            for const in known_constants:
                if const in content_lower or const in title_lower:
                    self.constant_map[const].append(unit)

    def match(self, classification: QueryClassification) -> list[RetrievalResult]:
        """Performs multi-key exact matching against extracted query entities."""
        matched_units: dict[str, tuple[KnowledgeUnit, float, str]] = {}

        # 1. Match on Extracted Symbols
        for sym in classification.extracted_symbols:
            sym_key = sym.strip().lower()
            for unit in self.symbol_map.get(sym_key, []):
                # Class / Function exact symbol matches are top score
                score = 1.0 if unit.source_type == "PYTHON_AST" else 0.95
                matched_units[unit.id] = (unit, score, f"Exact code symbol match for '{sym}'")

        # 2. Match on Extracted Routes
        for route in classification.extracted_routes:
            route_key = route.strip().lower()
            for unit in self.route_map.get(route_key, []):
                matched_units[unit.id] = (unit, 1.0, f"Exact API route match for '{route}'")
            # Try path only
            parts = route.split()
            if len(parts) == 2:
                path_key = parts[1].strip().lower()
                for unit in self.route_map.get(path_key, []):
                    if unit.id not in matched_units:
                        matched_units[unit.id] = (unit, 0.95, f"Exact route path match for '{parts[1]}'")

        # 3. Match on Extracted Actions / Components
        for action in classification.extracted_actions:
            action_key = action.strip().lower()
            for unit in self.constant_map.get(action_key, []):
                if unit.id not in matched_units:
                    matched_units[unit.id] = (unit, 0.95, f"Exact UI action match for '{action}'")

        for comp in classification.extracted_components:
            comp_key = comp.strip().lower()
            for unit in self.path_map.get(f"{comp_key}.tsx", []):
                if unit.id not in matched_units:
                    matched_units[unit.id] = (unit, 0.95, f"Exact UI component match for '{comp}'")
            for unit in self.symbol_map.get(comp_key, []):
                if unit.id not in matched_units:
                    matched_units[unit.id] = (unit, 0.95, f"Exact UI component symbol match for '{comp}'")

        # 4. Match on Extracted Scenario Constants
        if classification.extracted_scenario:
            scenario_key = classification.extracted_scenario.strip().lower()
            for unit in self.constant_map.get(scenario_key, []):
                if unit.id not in matched_units:
                    matched_units[unit.id] = (unit, 0.85, f"Exact scenario code match for '{classification.extracted_scenario}'")

        # Convert to RetrievalResult objects
        results: list[RetrievalResult] = []
        for unit, score, reason in matched_units.values():
            results.append(
                RetrievalResult(
                    knowledge_unit_id=unit.id,
                    title=unit.title,
                    content=unit.content,
                    summary=unit.summary,
                    domain=unit.domain,
                    source_tier=unit.source_tier,
                    authority=unit.authority,
                    source_type=unit.source_type,
                    source_path=unit.source_path,
                    line_start=unit.line_start,
                    line_end=unit.line_end,
                    symbol=unit.symbol,
                    route=unit.route,
                    frontend_action=unit.dynamic_tool_fallback,
                    score=score,
                    retrieval_method="EXACT",
                    dynamic_live_required=(unit.authority.value == "DYNAMIC_LIVE_REQUIRED"),
                    dynamic_tool_fallback=unit.dynamic_tool_fallback,
                    tags=unit.tags,
                    content_sha256=unit.content_sha256,
                    selection_reason=reason,
                    score_breakdown=RetrievalScoreBreakdown(
                        exact_score=score,
                        total_score=score,
                    ),
                )
            )

        return sorted(results, key=lambda r: r.score, reverse=True)
