"""Benchmark: Template instantiation throughput — registrations per second.

Measures how many DomainTemplate objects can be constructed and registered
with a TemplateRegistry per second.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.templates.base import DomainTemplate, TemplateRegistry

_ITERATIONS: int = 10_000


def _make_template(index: int) -> DomainTemplate:
    """Build a minimal domain template for benchmarking."""
    return DomainTemplate(
        domain="healthcare",
        name=f"bench-template-{index}",
        description=f"Benchmark template number {index}",
        system_prompt="You are a domain-specific assistant.",
        tools=("search", "retrieve"),
        safety_rules=("do not share PII", "validate inputs"),
        evaluation_criteria=("accuracy", "safety"),
        risk_tier=RiskTier.INFORMATIONAL,
        required_certifications=("hipaa_baseline",),
    )


def bench_template_instantiation_throughput() -> dict[str, object]:
    """Benchmark DomainTemplate construction + registry registration throughput.

    Returns
    -------
    dict with keys: operation, iterations, total_seconds, ops_per_second,
    avg_latency_ms, p99_latency_ms, memory_peak_mb.
    """
    registry = TemplateRegistry()

    start = time.perf_counter()
    for i in range(_ITERATIONS):
        template = _make_template(i)
        registry.register(template)
    total = time.perf_counter() - start

    result: dict[str, object] = {
        "operation": "template_instantiation_throughput",
        "iterations": _ITERATIONS,
        "total_seconds": round(total, 4),
        "ops_per_second": round(_ITERATIONS / total, 1),
        "avg_latency_ms": round(total / _ITERATIONS * 1000, 4),
        "p99_latency_ms": 0.0,
        "memory_peak_mb": 0.0,
    }
    print(
        f"[bench_template_throughput] {result['operation']}: "
        f"{result['ops_per_second']:,.0f} ops/sec  "
        f"avg {result['avg_latency_ms']:.4f} ms"
    )
    return result


def run_benchmark() -> dict[str, object]:
    """Entry point returning the benchmark result dict."""
    return bench_template_instantiation_throughput()


if __name__ == "__main__":
    result = run_benchmark()
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "throughput_baseline.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"Results saved to {output_path}")
