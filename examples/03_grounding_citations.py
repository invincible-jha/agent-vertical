#!/usr/bin/env python3
"""Example: Grounding, Citations, and Source Tracking

Demonstrates validating responses against a knowledge base,
generating citations, and tracing claims to sources.

Usage:
    python examples/03_grounding_citations.py

Requirements:
    pip install agent-vertical
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    Citation,
    CitationGenerator,
    ClaimTracer,
    DisclaimerGenerator,
    GroundingValidator,
    InMemoryKB,
    KnowledgeEntry,
    SourceReference,
    SourceTracker,
)


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    # Step 1: Build a knowledge base
    kb = InMemoryKB()
    entries = [
        KnowledgeEntry(
            entry_id="cdc-hypertension-2024",
            title="CDC Hypertension Guidelines 2024",
            content="High blood pressure is defined as 130/80 mmHg or above.",
            source_url="https://cdc.gov/hypertension/guidelines",
            domain="healthcare",
        ),
        KnowledgeEntry(
            entry_id="aha-cholesterol-2023",
            title="AHA Cholesterol Guidelines 2023",
            content="LDL cholesterol below 100 mg/dL is considered optimal.",
            source_url="https://heart.org/guidelines/cholesterol",
            domain="healthcare",
        ),
        KnowledgeEntry(
            entry_id="fda-drug-interactions",
            title="FDA Drug Interaction Reference",
            content="Beta-blockers may interact with certain antidepressants.",
            source_url="https://fda.gov/drugs/interactions",
            domain="healthcare",
        ),
    ]
    for entry in entries:
        kb.add(entry)
    print(f"Knowledge base: {kb.count()} entries")

    # Step 2: Validate grounding of a response
    validator = GroundingValidator(kb=kb)
    response = ("Blood pressure above 130/80 mmHg indicates hypertension. "
                "LDL cholesterol should remain below 100 mg/dL.")
    result = validator.validate(response=response)
    print(f"\nGrounding validation:")
    print(f"  Overall grounded: {result.is_grounded}")
    for sg in result.sentence_groundings:
        print(f"  [{sg.is_grounded}] '{sg.sentence[:60]}'")
        if sg.source_ids:
            print(f"    Sources: {sg.source_ids}")

    # Step 3: Generate citations
    gen = CitationGenerator(kb=kb)
    citations: list[Citation] = gen.generate(response=response)
    print(f"\nCitations ({len(citations)}):")
    for citation in citations:
        print(f"  [{citation.entry_id}] {citation.title}")
        print(f"    URL: {citation.source_url}")

    # Step 4: Disclaimer generation
    disclaimer_gen = DisclaimerGenerator()
    disclaimer = disclaimer_gen.generate(domain="healthcare", tone="standard")
    print(f"\nDisclaimer: {disclaimer[:100]}")

    # Step 5: Source tracking
    tracker = SourceTracker()
    for entry in entries:
        tracker.record(SourceReference(
            source_id=entry.entry_id,
            title=entry.title,
            url=entry.source_url,
        ))
    all_sources = tracker.list()
    print(f"\nTracked sources: {len(all_sources)}")


if __name__ == "__main__":
    main()
