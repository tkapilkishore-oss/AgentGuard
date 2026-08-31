"""Retrieval Quality & Performance Evaluation Benchmark Runner."""

import time
from collections import defaultdict
from typing import Sequence

from backend.app.retrieval.dataset import CANONICAL_EVALUATION_QUERIES, EvaluationQuery
from backend.app.retrieval.engine import RetrievalEngine
from backend.app.retrieval.models import (
    CategoryEvaluationMetric,
    EvaluationSummary,
    RetrievalResult,
)


class RetrievalEvaluator:
    """Runs automated quality, security, and performance benchmarks against the Retrieval Engine."""

    def __init__(self, engine: RetrievalEngine) -> None:
        self.engine = engine

    def run_benchmark(
        self,
        queries: Sequence[EvaluationQuery] | None = None,
    ) -> EvaluationSummary:
        """Executes the benchmark evaluation dataset and computes granular category metrics."""
        eval_queries = queries or CANONICAL_EVALUATION_QUERIES

        cat_metrics: dict[str, CategoryEvaluationMetric] = defaultdict(
            lambda: CategoryEvaluationMetric(category="")
        )

        total_queries = len(eval_queries)
        top1_total = 0
        top3_total = 0
        top5_total = 0
        domain_total = 0
        authority_total = 0
        dynamic_total = 0
        dynamic_count = 0
        code_total = 0
        code_count = 0
        fe_total = 0
        fe_count = 0
        secret_leakage = False

        # Measure Cold Query Latency on first query
        t0 = time.perf_counter()
        _ = self.engine.retrieve(eval_queries[0].query_text, top_k=5)
        cold_latency_ms = (time.perf_counter() - t0) * 1000.0

        warm_latencies: list[float] = []

        for q in eval_queries:
            cat_name = q.category
            cm = cat_metrics[cat_name]
            cm.category = cat_name
            cm.total_queries += 1

            # Time query execution
            t_start = time.perf_counter()
            results: list[RetrievalResult] = self.engine.retrieve(q.query_text, top_k=5)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            warm_latencies.append(elapsed_ms)

            # 1. Check Secret Leakage Invariant
            for r in results:
                path_lower = r.source_path.lower()
                if any(p in path_lower for p in [".env", "skills.md", "bug_findings.md", "node_modules"]):
                    secret_leakage = True

            # 2. Check Dynamic Live Classification
            classification = self.engine.classify_query(q.query_text)
            if q.is_dynamic:
                dynamic_count += 1
                if classification.is_dynamic_live and results and results[0].dynamic_live_required:
                    dynamic_total += 1
                    cm.dynamic_correct += 1

            # 3. Check Top-1 Hit
            top1_hit = False
            if results:
                r1 = results[0]
                # Domain match or target symbol/route/action match or dynamic match
                if (
                    r1.domain == q.expected_domain
                    or (q.expected_symbols and any(s.lower() in (r1.symbol or "").lower() for s in q.expected_symbols))
                    or (q.expected_routes and any(rt.lower() in (r1.route or "").lower() for rt in q.expected_routes))
                    or (q.expected_actions and any(a.lower() in r1.title.lower() or a.lower() in r1.content.lower() or (r1.frontend_action and a.lower() in r1.frontend_action.lower()) for a in q.expected_actions))
                    or (q.is_dynamic and r1.dynamic_live_required)
                ):
                    top1_hit = True
                    top1_total += 1
                    cm.top1_hits += 1

            # 4. Check Top-3 Hits
            top3_hit = False
            for r in results[:3]:
                if (
                    r.domain == q.expected_domain
                    or (q.expected_symbols and any(s.lower() in (r.symbol or "").lower() for s in q.expected_symbols))
                    or (q.expected_routes and any(rt.lower() in (r.route or "").lower() for rt in q.expected_routes))
                    or (q.expected_actions and any(a.lower() in r.title.lower() or a.lower() in r.content.lower() or (r.frontend_action and a.lower() in r.frontend_action.lower()) for a in q.expected_actions))
                    or (q.is_dynamic and r.dynamic_live_required)
                ):
                    top3_hit = True
                    break
            if top3_hit:
                top3_total += 1
                cm.top3_hits += 1

            # 5. Check Top-5 Hits
            top5_hit = False
            for r in results[:5]:
                if (
                    r.domain == q.expected_domain
                    or (q.expected_symbols and any(s.lower() in (r.symbol or "").lower() for s in q.expected_symbols))
                    or (q.expected_routes and any(rt.lower() in (r.route or "").lower() for rt in q.expected_routes))
                    or (q.expected_actions and any(a.lower() in r.title.lower() or a.lower() in r.content.lower() or (r.frontend_action and a.lower() in r.frontend_action.lower()) for a in q.expected_actions))
                    or (q.is_dynamic and r.dynamic_live_required)
                ):
                    top5_hit = True
                    break
            if top5_hit:
                top5_total += 1
                cm.top5_hits += 1

            # 6. Domain Accuracy in top 3
            if any(r.domain == q.expected_domain for r in results[:3]):
                domain_total += 1
                cm.domain_correct += 1

            # 7. Authority Accuracy in top 3
            if any(r.authority == q.expected_authority or (q.is_dynamic and r.dynamic_live_required) for r in results[:3]):
                authority_total += 1
                cm.authority_correct += 1

            # 8. Code Symbol Accuracy
            if q.expected_symbols:
                code_count += 1
                if any(any(s.lower() in (r.symbol or "").lower() or s.lower() in r.content.lower() for s in q.expected_symbols) for r in results[:3]):
                    code_total += 1

            # 9. Frontend Action Accuracy
            if q.expected_actions:
                fe_count += 1
                if any(any(a.lower() in r.title.lower() or a.lower() in (r.summary or "").lower() or a.lower() in r.content.lower() or (r.frontend_action and a.lower() in r.frontend_action.lower()) for a in q.expected_actions) for r in results[:3]):
                    fe_total += 1

        # Measure Repeated Query Latency
        t_rep_start = time.perf_counter()
        for _ in range(5):
            _ = self.engine.retrieve(eval_queries[0].query_text, top_k=5)
        rep_latency_ms = ((time.perf_counter() - t_rep_start) / 5.0) * 1000.0

        # Determinism check across 3 runs
        run1 = [self.engine.retrieve(q.query_text, top_k=3) for q in eval_queries[:5]]
        run2 = [self.engine.retrieve(q.query_text, top_k=3) for q in eval_queries[:5]]
        determinism_ok = True
        for r1_list, r2_list in zip(run1, run2):
            if [r.knowledge_unit_id for r in r1_list] != [r.knowledge_unit_id for r in r2_list]:
                determinism_ok = False
                break

        avg_warm_ms = sum(warm_latencies) / max(len(warm_latencies), 1)

        summary = EvaluationSummary(
            total_queries=total_queries,
            overall_top1_accuracy=round((top1_total / total_queries) * 100.0, 2),
            overall_top3_accuracy=round((top3_total / total_queries) * 100.0, 2),
            overall_top5_accuracy=round((top5_total / total_queries) * 100.0, 2),
            overall_domain_accuracy=round((domain_total / total_queries) * 100.0, 2),
            overall_authority_accuracy=round((authority_total / total_queries) * 100.0, 2),
            dynamic_classification_accuracy=round((dynamic_total / max(dynamic_count, 1)) * 100.0, 2),
            code_symbol_retrieval_accuracy=round((code_total / max(code_count, 1)) * 100.0, 2),
            frontend_action_retrieval_accuracy=round((fe_total / max(fe_count, 1)) * 100.0, 2),
            secret_leakage_detected=secret_leakage,
            determinism_verified=determinism_ok,
            categories=dict(cat_metrics),
            latency_cold_ms=round(cold_latency_ms, 2),
            latency_warm_ms=round(avg_warm_ms, 2),
            latency_repeated_ms=round(rep_latency_ms, 2),
        )

        return summary
