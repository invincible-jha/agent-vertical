#!/usr/bin/env python3
"""Example: Domain Templates

Demonstrates loading and using domain-specific agent templates
for healthcare, legal, and financial use cases.

Usage:
    python examples/02_domain_templates.py

Requirements:
    pip install agent-vertical
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    DomainTemplate,
    TemplateNotFoundError,
    TemplateRegistry,
    get_default_registry,
    load_all_templates,
)


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    # Step 1: Load and inspect the template registry
    load_all_templates()
    registry = get_default_registry()
    print(f"Registry: {registry.count()} templates loaded")

    all_templates = registry.list()
    print("\nAvailable templates:")
    for template in all_templates:
        print(f"  [{template.domain}] {template.template_id}: {template.name}")

    # Step 2: Access specific domain templates
    for template_id in ["clinical_documentation", "contract_review", "financial_report"]:
        try:
            template: DomainTemplate = registry.get(template_id)
            print(f"\nTemplate '{template.template_id}':")
            print(f"  Name: {template.name}")
            print(f"  Domain: {template.domain}")
            print(f"  System prompt (first 80 chars): {template.system_prompt[:80]}")
            print(f"  Required disclaimers: {len(template.required_disclaimers)}")
        except TemplateNotFoundError:
            print(f"\n  Template '{template_id}' not found.")

    # Step 3: Use a template to format a prompt
    try:
        template = registry.get("clinical_documentation")
        formatted = template.format_prompt(
            user_input="Summarise the patient's symptoms.",
            context={"patient_id": "P-12345", "visit_type": "follow-up"},
        )
        print(f"\nFormatted prompt (first 120 chars):")
        print(f"  {formatted[:120]}")
    except (TemplateNotFoundError, Exception) as error:
        print(f"Prompt formatting: {error}")


if __name__ == "__main__":
    main()
