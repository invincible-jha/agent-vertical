#!/usr/bin/env python3
"""Example: Domain Compliance Rules

Demonstrates applying domain-specific compliance rules for
healthcare, legal, and financial domains.

Usage:
    python examples/04_domain_compliance.py

Requirements:
    pip install agent-vertical
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    DomainComplianceChecker,
    DomainComplianceRules,
    RuleViolation,
    get_domain_rules,
    list_supported_domains,
)


def check_and_print(
    checker: DomainComplianceChecker,
    domain: str,
    response: str,
) -> None:
    result = checker.check(response)
    status = "PASS" if result.passed else "FAIL"
    print(f"\n  [{status}] {domain}: '{response[:60]}'")
    for v in result.violations:
        print(f"    Violation [{v.rule_id}]: {v.message[:70]}")


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    # List supported domains
    domains = list_supported_domains()
    print(f"Supported domains ({len(domains)}): {domains}")

    # Healthcare compliance
    hc_checker = DomainComplianceChecker("healthcare")
    print("\nHealthcare compliance:")
    check_and_print(
        hc_checker,
        "healthcare",
        "You should take 500mg of ibuprofen every 6 hours.",  # prescriptive
    )
    check_and_print(
        hc_checker,
        "healthcare",
        "This is general health information only. Please consult your doctor.",
    )

    # Legal compliance
    legal_checker = DomainComplianceChecker("legal")
    print("\nLegal compliance:")
    check_and_print(
        legal_checker,
        "legal",
        "You should definitely sue them — you will win.",  # legal advice
    )
    check_and_print(
        legal_checker,
        "legal",
        "This does not constitute legal advice. Please consult a qualified attorney.",
    )

    # Financial compliance
    finance_checker = DomainComplianceChecker("financial")
    print("\nFinancial compliance:")
    check_and_print(
        finance_checker,
        "financial",
        "Buy shares of ACME Corp — they will definitely rise 50% next quarter.",
    )
    check_and_print(
        finance_checker,
        "financial",
        "Past performance does not guarantee future results. "
        "Consult a financial adviser.",
    )

    # Inspect rules for a domain
    rules = get_domain_rules("healthcare")
    print(f"\nHealthcare rules ({rules.count()}):")
    for rule in rules.list()[:3]:
        print(f"  [{rule.rule_id}] {rule.rule_type.value}: {rule.description[:60]}")


if __name__ == "__main__":
    main()
