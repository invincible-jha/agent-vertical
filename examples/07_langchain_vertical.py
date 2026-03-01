#!/usr/bin/env python3
"""Example: LangChain Vertical Integration

Demonstrates using domain templates and compliance checks to wrap
LangChain chains for regulated domains.

Usage:
    python examples/07_langchain_vertical.py

Requirements:
    pip install agent-vertical
    pip install langchain   # optional — example degrades gracefully
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    DomainComplianceChecker,
    DisclaimerGenerator,
    GroundingValidator,
    InMemoryKB,
    KnowledgeEntry,
    get_default_registry,
    load_all_templates,
)

try:
    from langchain.schema.runnable import RunnableLambda
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False


def build_compliant_chain(
    domain: str,
    kb: InMemoryKB,
) -> "object":
    """Build a compliance-checked chain (uses LangChain if available)."""

    def raw_generate(input_text: str) -> str:
        return (f"General information: {input_text[:40]}... "
                "This does not constitute professional advice.")

    def compliant_handler(inputs: dict[str, str]) -> dict[str, object]:
        query = inputs.get("query", "")
        raw = raw_generate(query)

        checker = DomainComplianceChecker(domain)
        compliance = checker.check(raw)

        validator = GroundingValidator(kb=kb)
        grounding = validator.validate(response=raw)

        return {
            "response": raw,
            "compliant": compliance.passed,
            "grounded": grounding.is_grounded,
            "violations": len(compliance.violations),
        }

    if _LANGCHAIN_AVAILABLE:
        return RunnableLambda(compliant_handler)
    return compliant_handler  # type: ignore[return-value]


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    if not _LANGCHAIN_AVAILABLE:
        print("LangChain not installed — demonstrating compliance layer only.")
        print("Install with: pip install langchain")

    load_all_templates()
    registry = get_default_registry()
    print(f"Templates loaded: {registry.count()}")

    # Build knowledge base
    kb = InMemoryKB()
    kb.add(KnowledgeEntry(
        entry_id="guideline-001",
        title="General Health Guidelines",
        content="This information is for educational purposes only.",
        source_url="https://example.org/health",
        domain="healthcare",
    ))

    domain = "healthcare"
    chain = build_compliant_chain(domain, kb)

    # Add disclaimer
    disclaimer_gen = DisclaimerGenerator()
    disclaimer = disclaimer_gen.generate(domain=domain, tone="brief")
    print(f"\nDisclaimer: {disclaimer[:80]}")

    # Run queries through the compliant chain
    queries = [
        "What is blood pressure?",
        "Should I take medication for my condition?",
    ]

    print(f"\nCompliant {domain} chain results:")
    for query in queries:
        if _LANGCHAIN_AVAILABLE:
            result = chain.invoke({"query": query})  # type: ignore[union-attr]
        else:
            result = chain({"query": query})  # type: ignore[operator]

        print(f"\n  Query: '{query}'")
        print(f"  Response: '{str(result.get('response', ''))[:60]}'")
        print(f"  Compliant: {result.get('compliant')}")
        print(f"  Grounded: {result.get('grounded')}")
        print(f"  Violations: {result.get('violations')}")


if __name__ == "__main__":
    main()
