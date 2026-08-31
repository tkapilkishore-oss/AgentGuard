#!/usr/bin/env python
"""CLI Script to run and report Phase 5.5B-2 Retrieval Engine Evaluation Benchmarks."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.retrieval.engine import RetrievalEngine
from backend.app.retrieval.evaluation import RetrievalEvaluator


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentGuard Retrieval Engine Benchmark Runner")
    parser.add_argument("--knowledge-dir", type=str, default=None, help="Path to knowledge directory")
    args = parser.parse_args()

    print("=" * 70)
    print("  AGENTGUARD PHASE 5.5B-2 RETRIEVAL BENCHMARK EVALUATION")
    print("=" * 70)

    print("[*] Initializing Retrieval Engine from canonical knowledge assets...")
    engine = RetrievalEngine.from_knowledge_dir(args.knowledge_dir)
    evaluator = RetrievalEvaluator(engine)

    print(f"[*] Indexed {len(engine.units)} safe knowledge units.")
    print("[*] Running 41 Canonical Evaluation Queries across 17 Topic Categories...")

    summary = evaluator.run_benchmark()

    print("\n" + "-" * 70)
    print("  OVERALL RETRIEVAL QUALITY METRICS")
    print("-" * 70)
    print(f"  Total Queries Evaluated:          {summary.total_queries}")
    print(f"  Top-1 Relevance Accuracy:         {summary.overall_top1_accuracy:.2f}%")
    print(f"  Top-3 Relevance Accuracy:         {summary.overall_top3_accuracy:.2f}%")
    print(f"  Top-5 Relevance Accuracy:         {summary.overall_top5_accuracy:.2f}%")
    print(f"  Domain Retrieval Accuracy:        {summary.overall_domain_accuracy:.2f}%")
    print(f"  Authority Selection Accuracy:     {summary.overall_authority_accuracy:.2f}%")
    print(f"  Dynamic Query Safeguard Accuracy: {summary.dynamic_classification_accuracy:.2f}%")
    print(f"  Code Symbol Retrieval Accuracy:   {summary.code_symbol_retrieval_accuracy:.2f}%")
    print(f"  Frontend Action Accuracy:         {summary.frontend_action_retrieval_accuracy:.2f}%")
    print(f"  Secret Leakage Detected:          {'FAIL (LEAKAGE DETECTED)' if summary.secret_leakage_detected else 'PASS (CLEAN)'}")
    print(f"  Determinism Verified:             {'PASS (100% REPRODUCIBLE)' if summary.determinism_verified else 'FAIL'}")

    print("\n" + "-" * 70)
    print("  LATENCY PERFORMANCE METRICS")
    print("-" * 70)
    print(f"  Cold Query Latency:               {summary.latency_cold_ms:.2f} ms")
    print(f"  Warm Query Latency (avg):         {summary.latency_warm_ms:.2f} ms")
    print(f"  Repeated Query Latency (avg):     {summary.latency_repeated_ms:.2f} ms")

    print("\n" + "-" * 70)
    print("  CATEGORY-LEVEL BREAKDOWN")
    print("-" * 70)
    print(f"{'Category':<28} | {'Total':<5} | {'Top-1 (%)':<9} | {'Top-3 (%)':<9} | {'Top-5 (%)':<9}")
    print("-" * 70)
    for cat_name, m in summary.categories.items():
        print(f"{cat_name:<28} | {m.total_queries:<5} | {m.top1_accuracy:>8.1f}% | {m.top3_accuracy:>8.1f}% | {m.top5_accuracy:>8.1f}%")
    print("-" * 70)

    if summary.overall_top3_accuracy < 90.0:
        print(f"\n[!] QUALITY WARNING: Top-3 accuracy ({summary.overall_top3_accuracy:.1f}%) below 90% threshold.")
        return 1

    if summary.secret_leakage_detected:
        print("\n[!] CRITICAL SECURITY VIOLATION: Secret files or protected paths were returned.")
        return 1

    if not summary.determinism_verified:
        print("\n[!] DETERMINISM VIOLATION: Retrieval rankings were non-deterministic across repeated runs.")
        return 1

    print("\n[*] ALL BENCHMARK CRITERIA PASSED GREEN (Top-3 >= 90%, 0 Secrets, 100% Deterministic).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
