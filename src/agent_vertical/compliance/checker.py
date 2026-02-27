"""Domain compliance checker — pattern-based runtime compliance checking.

:class:`DomainComplianceChecker` evaluates an agent response against the
compliance rules for its domain, flagging prohibited phrases and verifying
that required disclaimers are present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_vertical.compliance.domain_rules import (
    ComplianceRule,
    DomainComplianceRules,
    RuleType,
    get_domain_rules,
)


@dataclass(frozen=True)
class RuleViolation:
    """A single compliance rule violation found in an agent response.

    Attributes
    ----------
    rule_id:
        The rule that was violated.
    rule_type:
        Whether this is a prohibited phrase or missing required disclaimer.
    description:
        Human-readable description of the violation.
    severity:
        Severity level of this violation.
    matched_text:
        The actual text fragment that triggered the violation (for prohibited
        rules) or an empty string (for missing required rules).
    remediation:
        Suggested fix.
    """

    rule_id: str
    rule_type: RuleType
    description: str
    severity: str
    matched_text: str
    remediation: str = ""


@dataclass
class ComplianceCheckResult:
    """Result of a domain compliance check.

    Attributes
    ----------
    domain:
        The domain that was checked.
    response_length:
        Number of characters in the checked response.
    is_compliant:
        ``True`` if no critical or high violations were found.
    violations:
        All violations found, ordered by severity.
    critical_violations:
        Subset of violations with severity ``"critical"``.
    high_violations:
        Subset of violations with severity ``"high"``.
    passed_rules:
        Number of rules that passed.
    total_rules:
        Total number of rules evaluated.
    """

    domain: str
    response_length: int
    is_compliant: bool
    violations: list[RuleViolation] = field(default_factory=list)
    critical_violations: list[RuleViolation] = field(default_factory=list)
    high_violations: list[RuleViolation] = field(default_factory=list)
    passed_rules: int = 0
    total_rules: int = 0

    @property
    def passed(self) -> bool:
        """Alias for ``is_compliant``."""
        return self.is_compliant


_SEVERITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def _check_prohibited(
    rule: ComplianceRule,
    response_lower: str,
    response_original: str,
) -> RuleViolation | None:
    """Return a violation if a prohibited phrase/pattern is found, else None."""
    if rule.is_regex:
        match = re.search(rule.pattern, response_lower, re.IGNORECASE)
        if match:
            return RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                description=rule.description,
                severity=rule.severity,
                matched_text=response_original[match.start():match.end()],
                remediation=rule.remediation,
            )
    else:
        idx = response_lower.find(rule.pattern.lower())
        if idx != -1:
            end = min(idx + len(rule.pattern), len(response_original))
            return RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                description=rule.description,
                severity=rule.severity,
                matched_text=response_original[idx:end],
                remediation=rule.remediation,
            )
    return None


def _check_required(
    rule: ComplianceRule,
    response_lower: str,
) -> RuleViolation | None:
    """Return a violation if a required phrase/pattern is missing, else None."""
    if rule.is_regex:
        if not re.search(rule.pattern, response_lower, re.IGNORECASE):
            return RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                description=rule.description,
                severity=rule.severity,
                matched_text="",
                remediation=rule.remediation,
            )
    else:
        if rule.pattern.lower() not in response_lower:
            return RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                description=rule.description,
                severity=rule.severity,
                matched_text="",
                remediation=rule.remediation,
            )
    return None


class DomainComplianceChecker:
    """Pattern-based compliance checker for domain-specific agent responses.

    :class:`DomainComplianceChecker` evaluates a response text against all
    compliance rules for the configured domain, identifying prohibited phrases
    and missing required disclaimers.

    Parameters
    ----------
    domain:
        Domain identifier.  The built-in rules for the domain are loaded
        automatically via :func:`~agent_vertical.compliance.domain_rules.get_domain_rules`.
    custom_rules:
        Optional additional :class:`DomainComplianceRules` to merge with the
        built-in rules.  Custom rules are appended after built-in rules.

    Example
    -------
    ::

        checker = DomainComplianceChecker("healthcare")
        result = checker.check(
            "You have diabetes. Take this medication twice daily."
        )
        print(result.is_compliant, len(result.critical_violations))
    """

    def __init__(
        self,
        domain: str,
        custom_rules: DomainComplianceRules | None = None,
    ) -> None:
        self._domain = domain.lower().strip()
        builtin = get_domain_rules(self._domain)
        merged_rules = list(builtin.rules)
        if custom_rules is not None:
            merged_rules.extend(custom_rules.rules)
        self._rules = DomainComplianceRules(domain=self._domain, rules=merged_rules)

    def check(self, response: str) -> ComplianceCheckResult:
        """Run all domain compliance rules against ``response``.

        Parameters
        ----------
        response:
            The full text of the agent response to check.

        Returns
        -------
        ComplianceCheckResult
            Detailed compliance result with all violations.
        """
        response_lower = response.lower()
        violations: list[RuleViolation] = []
        passed_count = 0

        for rule in self._rules.rules:
            violation: RuleViolation | None = None

            if rule.rule_type in (RuleType.PROHIBITED_PHRASE, RuleType.PROHIBITED_PATTERN):
                violation = _check_prohibited(rule, response_lower, response)
            elif rule.rule_type in (RuleType.REQUIRED_DISCLAIMER, RuleType.REQUIRED_PATTERN):
                violation = _check_required(rule, response_lower)

            if violation is not None:
                violations.append(violation)
            else:
                passed_count += 1

        # Sort by severity (critical first)
        violations.sort(key=lambda v: _SEVERITY_ORDER.get(v.severity, 99))

        critical = [v for v in violations if v.severity == "critical"]
        high = [v for v in violations if v.severity == "high"]

        is_compliant = len(critical) == 0 and len(high) == 0

        return ComplianceCheckResult(
            domain=self._domain,
            response_length=len(response),
            is_compliant=is_compliant,
            violations=violations,
            critical_violations=critical,
            high_violations=high,
            passed_rules=passed_count,
            total_rules=len(self._rules.rules),
        )

    def check_batch(self, responses: list[str]) -> list[ComplianceCheckResult]:
        """Run compliance checks on multiple responses.

        Parameters
        ----------
        responses:
            List of agent response texts to check.

        Returns
        -------
        list[ComplianceCheckResult]
            One result per response, in the same order.
        """
        return [self.check(response) for response in responses]
