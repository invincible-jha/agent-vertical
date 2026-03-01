#!/usr/bin/env python3
"""Example: Quickstart — agent-vertical

Minimal working example: load domain templates, run a compliance
check, and execute a benchmark scenario.

Usage:
    python examples/01_quickstart.py

Requirements:
    pip install agent-vertical
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    Template,
    DomainComplianceChecker,
    BenchmarkRunner,
    get_default_registry,
    list_supported_domains,
    load_all_templates,
)


def my_agent(user_input: str) -> str:
    """Simple agent stub for demonstration."""
    return (f"This information is for educational purposes only and does not "
            f"constitute professional advice. Regarding your question: {user_input[:40]}")


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    # Step 1: Load all built-in domain templates
    load_all_templates()
    registry = get_default_registry()
    print(f"Templates loaded: {registry.count()}")

    # Step 2: List supported compliance domains
    domains = list_supported_domains()
    print(f"Supported compliance domains: {domains[:5]}")

    # Step 3: Run domain compliance check
    checker = DomainComplianceChecker("healthcare")
    response = ("This does not constitute medical advice. "
                "Please consult a licensed physician.")
    result = checker.check(response)
    print(f"\nHealthcare compliance check:")
    print(f"  Passed: {result.passed}")
    print(f"  Violations: {len(result.violations)}")

    # Step 4: Run domain benchmark
    runner = BenchmarkRunner(agent=my_agent, agent_name="DemoAgent v1")
    report = runner.run_domain("healthcare", max_scenarios=3)
    print(f"\nBenchmark report (healthcare, {report.total_scenarios} scenarios):")
    print(f"  Pass rate: {report.pass_rate:.0%}")
    print(f"  {report.summary_text()[:100]}")


if __name__ == "__main__":
    main()
