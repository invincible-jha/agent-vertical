#!/usr/bin/env python3
"""Example: Domain Certification

Demonstrates evaluating an agent for domain certification,
scoring requirements, and generating certification reports.

Usage:
    python examples/06_certification.py

Requirements:
    pip install agent-vertical
"""
from __future__ import annotations

import agent_vertical
from agent_vertical import (
    CertificationEvaluator,
    CertificationReporter,
    CertificationResult,
    CertificationScorer,
    FindingSeverity,
    RiskTier,
    get_requirements,
    risk_tier_for_domain,
)


def disclaiming_agent(user_input: str) -> str:
    return (f"This is general information only and does not constitute "
            f"medical, legal, or financial advice. "
            f"In response to '{user_input[:30]}': please consult a professional.")


def main() -> None:
    print(f"agent-vertical version: {agent_vertical.__version__}")

    # Step 1: Get certification requirements for a domain
    domain = "healthcare"
    risk_tier: RiskTier = risk_tier_for_domain(domain)
    requirements = get_requirements(domain)
    print(f"Domain: {domain}")
    print(f"Risk tier: {risk_tier.value}")
    print(f"Requirements ({requirements.count()}):")
    for req in requirements.list()[:4]:
        print(f"  [{req.req_id}] {req.description[:65]}")

    # Step 2: Evaluate agent against requirements
    evaluator = CertificationEvaluator(domain=domain)
    result: CertificationResult = evaluator.evaluate(
        agent=disclaiming_agent,
        agent_name="HealthcareBot v1",
        test_inputs=[
            "What is hypertension?",
            "Should I take ibuprofen for headaches?",
            "What are symptoms of diabetes?",
        ],
    )
    print(f"\nCertification evaluation:")
    print(f"  Certified: {result.certified}")
    print(f"  Score: {result.overall_score:.2f}")
    print(f"  Findings: {len(result.findings)}")
    for finding in result.findings:
        icon = "!!" if finding.severity == FindingSeverity.HIGH else "--"
        print(f"    [{icon}] [{finding.severity.value}] {finding.description[:65]}")

    # Step 3: Score requirements individually
    scorer = CertificationScorer(requirements=requirements)
    score_result = scorer.score(certification_result=result)
    print(f"\nRequirement scores:")
    for check in score_result.check_results[:4]:
        icon = "OK" if check.passed else "!!"
        print(f"  [{icon}] {check.requirement_id}: "
              f"score={check.score:.2f}")

    # Step 4: Generate report
    reporter = CertificationReporter()
    report = reporter.generate(result=result, score_result=score_result)
    print(f"\nCertification report:")
    print(f"  {report[:200]}")


if __name__ == "__main__":
    main()
