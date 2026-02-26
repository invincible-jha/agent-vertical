"""Benchmarks subsystem — scenario library, evaluation, and reporting.

Provides 40 realistic benchmark scenarios across 4 domains (10 per domain)
with a runner that orchestrates evaluation and produces structured reports.

Example
-------
::

    from agent_vertical.benchmarks import BenchmarkRunner, ScenarioLibrary

    library = ScenarioLibrary()
    print(f"Total scenarios: {len(library)}")

    def my_agent(user_input: str) -> str:
        return "This does not constitute medical advice. Please consult a clinician."

    runner = BenchmarkRunner(my_agent, agent_name="MyAgent v1")
    report = runner.run_domain("healthcare")
    print(report.summary_text())
"""
from __future__ import annotations

from agent_vertical.benchmarks.evaluator import (
    BehaviourCheck,
    ScenarioEvaluator,
    ScenarioResult,
)
from agent_vertical.benchmarks.runner import (
    AgentResponseCallable,
    BenchmarkReport,
    BenchmarkRunner,
    DomainBenchmarkSummary,
)
from agent_vertical.benchmarks.scenarios import (
    BenchmarkScenario,
    ScenarioLibrary,
)

__all__ = [
    "AgentResponseCallable",
    "BehaviourCheck",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BenchmarkScenario",
    "DomainBenchmarkSummary",
    "ScenarioEvaluator",
    "ScenarioLibrary",
    "ScenarioResult",
]
