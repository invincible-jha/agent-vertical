"""Automated certification checks for vertical agent templates.

Provides a library of rule-based checks that can be run automatically
against a template definition or agent configuration dict, without
requiring human review.  Each check returns a :class:`CheckResult`
compatible with the existing :class:`CertificationScorer`.

Check categories
----------------
- Structural checks: required keys and value types present.
- Disclaimer checks: mandatory disclaimer text patterns.
- Security checks: input validation, rate-limiting declarations.
- Metadata checks: version, domain, risk_tier fields.
- Grounding checks: sources and citation fields present.
"""
from __future__ import annotations

import re

from agent_vertical.certification.scorer import CheckResult, FindingSeverity


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def check_has_domain(config: dict[str, object]) -> CheckResult:
    """Verify the template declares a non-empty domain field.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["domain"]`` is a non-empty string.
    """
    passed = bool(config.get("domain") and isinstance(config["domain"], str))
    return CheckResult(
        check_id="struct.has_domain",
        check_name="Domain Declared",
        passed=passed,
        severity=FindingSeverity.HIGH,
        description="Template must declare a non-empty 'domain' field.",
        detail="" if passed else "Missing or empty 'domain' field.",
    )


def check_has_risk_tier(config: dict[str, object]) -> CheckResult:
    """Verify the template declares a valid risk_tier field.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["risk_tier"]`` is a recognised tier string.
    """
    valid_tiers = {"informational", "advisory", "decision_support"}
    value = config.get("risk_tier", "")
    passed = isinstance(value, str) and value.lower() in valid_tiers
    return CheckResult(
        check_id="struct.has_risk_tier",
        check_name="Risk Tier Declared",
        passed=passed,
        severity=FindingSeverity.HIGH,
        description="Template must declare a valid 'risk_tier' field.",
        detail="" if passed else f"Invalid or missing risk_tier: {value!r}",
    )


def check_has_version(config: dict[str, object]) -> CheckResult:
    """Verify the template declares a semantic version string.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["version"]`` matches MAJOR.MINOR.PATCH.
    """
    version = config.get("version", "")
    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    passed = isinstance(version, str) and bool(pattern.match(version))
    return CheckResult(
        check_id="struct.has_version",
        check_name="Semantic Version",
        passed=passed,
        severity=FindingSeverity.MEDIUM,
        description="Template must declare a semantic version (e.g. '1.0.0').",
        detail="" if passed else f"Invalid or missing version: {version!r}",
    )


def check_has_disclaimer(config: dict[str, object]) -> CheckResult:
    """Verify the template includes a non-empty disclaimer.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["disclaimer"]`` is a non-empty string.
    """
    disclaimer = config.get("disclaimer", "")
    passed = bool(disclaimer and isinstance(disclaimer, str) and len(disclaimer.strip()) > 10)
    return CheckResult(
        check_id="disclaimer.present",
        check_name="Disclaimer Present",
        passed=passed,
        severity=FindingSeverity.CRITICAL,
        description="Template must include a non-empty disclaimer statement.",
        detail="" if passed else "Missing or too short 'disclaimer' field.",
    )


def check_disclaimer_not_advice(config: dict[str, object]) -> CheckResult:
    """Verify the disclaimer contains a 'not advice' statement.

    The disclaimer must contain one of the recognised not-advice phrases
    to ensure users are informed that the output is not professional advice.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when the disclaimer text contains a not-advice phrase.
    """
    disclaimer = config.get("disclaimer", "")
    if not isinstance(disclaimer, str):
        disclaimer = ""
    lowered = disclaimer.lower()
    not_advice_phrases = [
        "not.*advice",
        "does not constitute.*advice",
        "informational purposes only",
        "not a substitute",
        "consult.*professional",
    ]
    passed = any(re.search(phrase, lowered) for phrase in not_advice_phrases)
    return CheckResult(
        check_id="disclaimer.not_advice",
        check_name="Disclaimer: Not-Advice Statement",
        passed=passed,
        severity=FindingSeverity.CRITICAL,
        description=(
            "Disclaimer must contain a statement that output is not professional advice."
        ),
        detail="" if passed else "Disclaimer lacks a clear not-advice statement.",
    )


def check_input_validation_declared(config: dict[str, object]) -> CheckResult:
    """Verify the template declares input validation configuration.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["input_validation"]`` is truthy.
    """
    passed = bool(config.get("input_validation"))
    return CheckResult(
        check_id="security.input_validation",
        check_name="Input Validation Declared",
        passed=passed,
        severity=FindingSeverity.HIGH,
        description="Template must declare input validation configuration.",
        detail="" if passed else "Missing 'input_validation' configuration.",
    )


def check_rate_limiting_declared(config: dict[str, object]) -> CheckResult:
    """Verify the template declares rate-limiting configuration.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["rate_limiting"]`` is truthy.
    """
    passed = bool(config.get("rate_limiting"))
    return CheckResult(
        check_id="security.rate_limiting",
        check_name="Rate Limiting Declared",
        passed=passed,
        severity=FindingSeverity.MEDIUM,
        description="Template must declare rate-limiting configuration.",
        detail="" if passed else "Missing 'rate_limiting' configuration.",
    )


def check_has_sources(config: dict[str, object]) -> CheckResult:
    """Verify the template declares at least one knowledge source.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["sources"]`` is a non-empty list.
    """
    sources = config.get("sources", [])
    passed = isinstance(sources, list) and len(sources) > 0
    return CheckResult(
        check_id="grounding.has_sources",
        check_name="Knowledge Sources Declared",
        passed=passed,
        severity=FindingSeverity.HIGH,
        description="Template must list at least one knowledge source.",
        detail="" if passed else "Empty or missing 'sources' list.",
    )


def check_has_description(config: dict[str, object]) -> CheckResult:
    """Verify the template provides a meaningful description.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["description"]`` is a string of at least 20 chars.
    """
    description = config.get("description", "")
    passed = isinstance(description, str) and len(description.strip()) >= 20
    return CheckResult(
        check_id="metadata.has_description",
        check_name="Description Present",
        passed=passed,
        severity=FindingSeverity.LOW,
        description="Template must include a description of at least 20 characters.",
        detail="" if passed else "Missing or too short 'description' field.",
    )


def check_human_review_gate(config: dict[str, object]) -> CheckResult:
    """Verify that decision-support templates declare a human review gate.

    Only applies when risk_tier is 'decision_support'.  Returns a passing
    INFO-level result for lower tiers.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed unless risk_tier is 'decision_support' and
        ``human_review_gate`` is absent/False.
    """
    tier = str(config.get("risk_tier", "")).lower()
    if tier != "decision_support":
        return CheckResult(
            check_id="governance.human_review_gate",
            check_name="Human Review Gate",
            passed=True,
            severity=FindingSeverity.INFO,
            description="Human review gate only required for decision_support tier.",
            detail="Not applicable at this risk tier.",
        )
    passed = bool(config.get("human_review_gate"))
    return CheckResult(
        check_id="governance.human_review_gate",
        check_name="Human Review Gate",
        passed=passed,
        severity=FindingSeverity.CRITICAL,
        description=(
            "Decision-support templates must declare a human review gate "
            "for actions that affect real-world outcomes."
        ),
        detail="" if passed else "Missing 'human_review_gate' for decision_support tier.",
    )


def check_audit_trail_declared(config: dict[str, object]) -> CheckResult:
    """Verify the template declares audit trail configuration.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.

    Returns
    -------
    CheckResult
        Passed when ``config["audit_trail"]`` is truthy.
    """
    passed = bool(config.get("audit_trail"))
    return CheckResult(
        check_id="governance.audit_trail",
        check_name="Audit Trail Declared",
        passed=passed,
        severity=FindingSeverity.HIGH,
        description="Template must declare audit trail configuration.",
        detail="" if passed else "Missing 'audit_trail' configuration.",
    )


# ---------------------------------------------------------------------------
# Check suite runner
# ---------------------------------------------------------------------------

#: Default ordered suite of automated checks.
DEFAULT_CHECKS: list = [
    check_has_domain,
    check_has_risk_tier,
    check_has_version,
    check_has_disclaimer,
    check_disclaimer_not_advice,
    check_input_validation_declared,
    check_rate_limiting_declared,
    check_has_sources,
    check_has_description,
    check_human_review_gate,
    check_audit_trail_declared,
]


def run_automated_checks(
    config: dict[str, object],
    checks: list | None = None,
) -> list[CheckResult]:
    """Run a suite of automated checks against *config*.

    Parameters
    ----------
    config:
        Template or agent configuration dictionary.
    checks:
        List of check callables to run.  Defaults to :data:`DEFAULT_CHECKS`.

    Returns
    -------
    list[CheckResult]
        One result per check, in the order the checks were run.
    """
    suite = checks if checks is not None else DEFAULT_CHECKS
    return [check(config) for check in suite]


__all__ = [
    "DEFAULT_CHECKS",
    "check_audit_trail_declared",
    "check_disclaimer_not_advice",
    "check_has_description",
    "check_has_disclaimer",
    "check_has_domain",
    "check_has_risk_tier",
    "check_has_sources",
    "check_has_version",
    "check_human_review_gate",
    "check_input_validation_declared",
    "check_rate_limiting_declared",
    "run_automated_checks",
]
