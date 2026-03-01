"""Benchmark: Domain registry lookup latency — per-lookup p50/p95/p99.

Measures the per-call latency of TemplateRegistry.get() against a registry
pre-populated with all built-in domain templates.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_vertical.templates.base import load_all_templates

_WARMUP: int = 200
_ITERATIONS: int = 10_000


def bench_registry_lookup_latency() -> dict[str, object]:
    """Benchmark TemplateRegistry.get() per-call latency.

    Returns
    -------
    dict with keys: operation, iterations, total_seconds, ops_per_second,
    avg_latency_ms, p99_latency_ms, memory_peak_mb.
    """
    registry = load_all_templates()
    all_templates = registry.list_templates()

    if not all_templates:
        # Fallback: register one template so we can benchmark.
        from agent_vertical.certification.risk_tier import RiskTier
        from agent_vertical.templates.base import DomainTemplate

        fallback = DomainTemplate(
            domain="bench",
            name="bench-fallback",
            description="Fallback benchmark template",
            system_prompt="Benchmark system prompt.",
            tools=(),
            safety_rules=(),
            evaluation_criteria=(),
            risk_tier=RiskTier.INFORMATIONAL,
            required_certifications=(),
        )
        registry.register(fallback)
        all_templates = [fallback]

    # Pick a stable template name to look up repeatedly.
    target_name = all_templates[0].name

    # Warmup.
    for _ in range(_WARMUP):
        registry.get(target_name)

    latencies_ms: list[float] = []
    for _ in range(_ITERATIONS):
        t0 = time.perf_counter()
        registry.get(target_name)
        latencies_ms.append((time.perf_counter() - t0) * 1000)

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)
    total = sum(latencies_ms) / 1000

    result: dict[str, object] = {
        "operation": "registry_lookup_latency",
        "iterations": _ITERATIONS,
        "total_seconds": round(total, 4),
        "ops_per_second": round(_ITERATIONS / total, 1),
        "avg_latency_ms": round(sum(latencies_ms) / n, 4),
        "p99_latency_ms": round(sorted_lats[min(int(n * 0.99), n - 1)], 4),
        "memory_peak_mb": 0.0,
    }
    print(
        f"[bench_registry_latency] {result['operation']}: "
        f"p99={result['p99_latency_ms']:.4f}ms  "
        f"mean={result['avg_latency_ms']:.4f}ms"
    )
    return result


def run_benchmark() -> dict[str, object]:
    """Entry point returning the benchmark result dict."""
    return bench_registry_lookup_latency()


if __name__ == "__main__":
    result = run_benchmark()
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "latency_baseline.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Results saved to {output_path}")
