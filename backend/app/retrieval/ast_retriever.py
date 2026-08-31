"""AST & Codebase Cross-Reference Retriever for Symbols, Routes, Handlers, and Tests."""

from collections import defaultdict
from typing import Any

from backend.app.knowledge.models import CodeRelationship, KnowledgeUnit
from backend.app.retrieval.models import QueryClassification, RetrievalResult, RetrievalScoreBreakdown


class AstCodeRetriever:
    """Navigates AST symbol relationships, linking functions to routes, handlers, and tests."""

    def __init__(self, units: list[KnowledgeUnit]) -> None:
        self.units = units
        self.symbol_to_units: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.route_to_units: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.test_to_units: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.path_to_units: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        self.relationship_graph: dict[str, list[CodeRelationship]] = defaultdict(list)

        self._index_ast()

    def _index_ast(self) -> None:
        for unit in self.units:
            if unit.symbol:
                self.symbol_to_units[unit.symbol.lower()].append(unit)
                if "." in unit.symbol:
                    unqual = unit.symbol.split(".")[-1].lower()
                    self.symbol_to_units[unqual].append(unit)

            if unit.route:
                self.route_to_units[unit.route.lower()].append(unit)
                parts = unit.route.split()
                if len(parts) == 2:
                    self.route_to_units[parts[1].lower()].append(unit)

            if unit.source_type == "PYTEST":
                if unit.symbol:
                    self.test_to_units[unit.symbol.lower()].append(unit)

            if unit.source_path:
                self.path_to_units[unit.source_path.lower()].append(unit)

            for rel in unit.relationships:
                self.relationship_graph[rel.source_symbol.lower()].append(rel)

    def find_symbol_evidence(self, symbol_name: str) -> list[RetrievalResult]:
        """Finds direct AST symbol evidence plus associated tests and callers."""
        clean_name = symbol_name.strip().lower()
        direct_units = self.symbol_to_units.get(clean_name, [])

        results: list[RetrievalResult] = []
        seen_ids = set()

        for u in direct_units:
            if u.id in seen_ids:
                continue
            seen_ids.add(u.id)

            rel_summary = [f"{r.relationship_type} -> {r.target_symbol}" for r in u.relationships]
            rel_text = f" (Relations: {', '.join(rel_summary)})" if rel_summary else ""

            results.append(
                RetrievalResult(
                    knowledge_unit_id=u.id,
                    title=u.title,
                    content=u.content,
                    summary=u.summary,
                    domain=u.domain,
                    source_tier=u.source_tier,
                    authority=u.authority,
                    source_type=u.source_type,
                    source_path=u.source_path,
                    line_start=u.line_start,
                    line_end=u.line_end,
                    symbol=u.symbol,
                    route=u.route,
                    frontend_action=u.dynamic_tool_fallback,
                    score=1.0,
                    retrieval_method="AST_SYMBOL",
                    dynamic_live_required=False,
                    dynamic_tool_fallback=u.dynamic_tool_fallback,
                    tags=u.tags,
                    content_sha256=u.content_sha256,
                    selection_reason=f"AST direct symbol extraction for '{u.symbol}' in {u.source_path}:{u.line_start}-{u.line_end}{rel_text}",
                    score_breakdown=RetrievalScoreBreakdown(
                        exact_score=1.0,
                        authority_score=0.95,
                        total_score=1.0,
                    ),
                )
            )

        return results

    def find_code_trace(
        self,
        frontend_action: str | None = None,
        route_path: str | None = None,
        symbol_name: str | None = None,
    ) -> dict[str, list[KnowledgeUnit]]:
        """Reconstructs the full vertical trace: UI Component -> Route -> Handler/Policy -> Test."""
        trace: dict[str, list[KnowledgeUnit]] = {
            "ui": [],
            "route": [],
            "logic": [],
            "tests": [],
        }

        # 1. UI components matching action
        if frontend_action:
            action_lower = frontend_action.lower()
            for u in self.units:
                if u.source_type == "TSX_COMPONENT" and (
                    action_lower in u.title.lower() or action_lower in u.content.lower()
                ):
                    trace["ui"].append(u)

        # 2. Routes matching route path or action
        if route_path:
            clean_route = route_path.lower()
            trace["route"].extend(self.route_to_units.get(clean_route, []))

        # 3. Logic & Policy symbols
        if symbol_name:
            clean_sym = symbol_name.lower()
            trace["logic"].extend(self.symbol_to_units.get(clean_sym, []))

        # 4. Tests matching symbols or routes
        all_symbols = [u.symbol for u in trace["logic"] if u.symbol]
        for s in all_symbols:
            s_lower = s.lower()
            # A. Check explicit relationship graph links
            for rel in self.relationship_graph.get(s_lower, []):
                target_lower = rel.target_symbol.lower()
                for t in self.test_to_units.get(target_lower, []):
                    if t not in trace["tests"]:
                        trace["tests"].append(t)
            # B. Check content/docstring matching
            for t_unit in self.test_to_units.values():
                for t in t_unit:
                    if (s_lower in t.content.lower() or s_lower in t.summary.lower()) and t not in trace["tests"]:
                        trace["tests"].append(t)

        return trace
