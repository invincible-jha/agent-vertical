"""Benchmark: Memory usage of template registry population and lookup.

Uses tracemalloc to measure peak memory allocated during mass template
registration and repeated lookup operations.
"""
from __future__ import annotations

import json
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.templates.base import DomainTemplate, TemplateRegistry

_TEMPLATE_COUNT: int = 200
_LOOKUP_ITERATIONS: int = 500


def bench_registry_memory_usage() -> dict[str, object]:
    """Benchmark memory usage when populating and querying a template registry.

    Returns
    -------
    dict with keys: operation, iterations, peak_memory_kb, current_memory_kb,
    ops_per_second, avg_latency_ms, memory_peak_mb.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    registry = TemplateRegistry()

    for i in range(_TEMPLATE_COUNT):
        template = DomainTemplate(
            domain="bench",
            name=f"mem-bench-template-{i}",
            description=f"Memory benchmark template {i}",
            system_prompt="System prompt for memory benchmark.",
            tools=("search", "retrieve", "summarize"),
            safety_rules=("rule-1", "rule-2"),
            evaluation_criteria=("accuracy",),
            risk_tier=RiskTier.ADVISORY,
            required_certifications=(),
        )
        registry.register(template)

    for i in range(_LOOKUP_ITERATIONS):
        idx = i % _TEMPLATE_COUNT
        registry.get(f"mem-bench-template-{idx}")

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_bytes = sum(stat.size_diff for stat in stats if stat.size_diff > 0)
    peak_kb = round(total_bytes / 1024, 2)

    result: dict[str, object] = {
        "operation": "registry_memory_usage",
        "iterations": _TEMPLATE_COUNT + _LOOKUP_ITERATIONS,
        "peak_memory_kb": peak_kb,
        "current_memory_kb": peak_kb,
        "ops_per_second": 0.0,
        "avg_latency_ms": 0.0,
        "memory_peak_mb": round(peak_kb / 1024, 4),
    }
    print(
        f"[bench_memory_usage] {result['operation']}: "
        f"peak {peak_kb:.2f} KB over "
        f"{_TEMPLATE_COUNT} registrations + {_LOOKUP_ITERATIONS} lookups"
    )
    return result


def run_benchmark() -> dict[str, object]:
    """Entry point returning the benchmark result dict."""
    return bench_registry_memory_usage()


if __name__ == "__main__":
    result = run_benchmark()
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "memory_baseline.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Results saved to {output_path}")
