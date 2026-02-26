"""Compliance subsystem — domain-specific runtime compliance checking.

Provides pattern-based checking for prohibited phrases and required
disclaimers across healthcare, finance, legal, and education domains.

Example
-------
::

    from agent_vertical.compliance import DomainComplianceChecker

    checker = DomainComplianceChecker("healthcare")
    result = checker.check("This does not constitute medical advice. Consult a clinician.")
    print(result.is_compliant)
"""
from __future__ import annotations

from agent_vertical.compliance.checker import (
    ComplianceCheckResult,
    DomainComplianceChecker,
    RuleViolation,
)
from agent_vertical.compliance.domain_rules import (
    ComplianceRule,
    DomainComplianceRules,
    RuleType,
    get_domain_rules,
    list_supported_domains,
)

__all__ = [
    "ComplianceCheckResult",
    "ComplianceRule",
    "DomainComplianceChecker",
    "DomainComplianceRules",
    "RuleType",
    "RuleViolation",
    "get_domain_rules",
    "list_supported_domains",
]
