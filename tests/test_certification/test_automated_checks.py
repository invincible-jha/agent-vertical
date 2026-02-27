"""Tests for agent_vertical.certification.automated_checks."""
from __future__ import annotations

from typing import Any

import pytest

from agent_vertical.certification.automated_checks import (
    DEFAULT_CHECKS,
    check_audit_trail_declared,
    check_disclaimer_not_advice,
    check_has_description,
    check_has_disclaimer,
    check_has_domain,
    check_has_risk_tier,
    check_has_sources,
    check_has_version,
    check_human_review_gate,
    check_input_validation_declared,
    check_rate_limiting_declared,
    run_automated_checks,
)
from agent_vertical.certification.scorer import FindingSeverity


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _full_config() -> dict[str, Any]:
    """Return a fully-compliant template config."""
    return {
        "domain": "healthcare",
        "risk_tier": "advisory",
        "version": "1.2.3",
        "disclaimer": (
            "This output is not medical advice and does not constitute a "
            "substitute for professional consultation."
        ),
        "input_validation": {"enabled": True, "max_length": 2000},
        "rate_limiting": {"requests_per_minute": 60},
        "sources": ["clinical_guidelines_v2", "medline_2024"],
        "description": "A healthcare assistant for general medical information lookup.",
        "audit_trail": {"enabled": True, "backend": "s3"},
    }


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


class TestCheckHasDomain:
    def test_passes_with_valid_domain(self) -> None:
        result = check_has_domain({"domain": "healthcare"})
        assert result.passed is True

    def test_fails_with_missing_domain(self) -> None:
        result = check_has_domain({})
        assert result.passed is False

    def test_fails_with_empty_domain(self) -> None:
        result = check_has_domain({"domain": ""})
        assert result.passed is False

    def test_fails_with_non_string_domain(self) -> None:
        result = check_has_domain({"domain": 42})
        assert result.passed is False

    def test_severity_is_high(self) -> None:
        result = check_has_domain({})
        assert result.severity == FindingSeverity.HIGH


class TestCheckHasRiskTier:
    def test_passes_with_informational(self) -> None:
        result = check_has_risk_tier({"risk_tier": "informational"})
        assert result.passed is True

    def test_passes_with_advisory(self) -> None:
        result = check_has_risk_tier({"risk_tier": "advisory"})
        assert result.passed is True

    def test_passes_with_decision_support(self) -> None:
        result = check_has_risk_tier({"risk_tier": "decision_support"})
        assert result.passed is True

    def test_fails_with_invalid_tier(self) -> None:
        result = check_has_risk_tier({"risk_tier": "critical"})
        assert result.passed is False

    def test_fails_with_missing_tier(self) -> None:
        result = check_has_risk_tier({})
        assert result.passed is False

    def test_case_insensitive(self) -> None:
        result = check_has_risk_tier({"risk_tier": "ADVISORY"})
        assert result.passed is True


class TestCheckHasVersion:
    def test_passes_with_valid_semver(self) -> None:
        result = check_has_version({"version": "1.2.3"})
        assert result.passed is True

    def test_passes_with_zero_versions(self) -> None:
        result = check_has_version({"version": "0.0.1"})
        assert result.passed is True

    def test_fails_with_missing_patch(self) -> None:
        result = check_has_version({"version": "1.2"})
        assert result.passed is False

    def test_fails_with_non_numeric(self) -> None:
        result = check_has_version({"version": "v1.2.3"})
        assert result.passed is False

    def test_fails_with_missing_version(self) -> None:
        result = check_has_version({})
        assert result.passed is False

    def test_severity_is_medium(self) -> None:
        result = check_has_version({})
        assert result.severity == FindingSeverity.MEDIUM


# ---------------------------------------------------------------------------
# Disclaimer checks
# ---------------------------------------------------------------------------


class TestCheckHasDisclaimer:
    def test_passes_with_valid_disclaimer(self) -> None:
        result = check_has_disclaimer({"disclaimer": "This is not medical advice, consult your doctor."})
        assert result.passed is True

    def test_fails_with_missing_disclaimer(self) -> None:
        result = check_has_disclaimer({})
        assert result.passed is False

    def test_fails_with_short_disclaimer(self) -> None:
        result = check_has_disclaimer({"disclaimer": "Short"})
        assert result.passed is False

    def test_severity_is_critical(self) -> None:
        result = check_has_disclaimer({})
        assert result.severity == FindingSeverity.CRITICAL


class TestCheckDisclaimerNotAdvice:
    def test_passes_with_not_advice_phrase(self) -> None:
        result = check_disclaimer_not_advice({
            "disclaimer": "This does not constitute medical advice."
        })
        assert result.passed is True

    def test_passes_with_informational_purposes(self) -> None:
        result = check_disclaimer_not_advice({
            "disclaimer": "For informational purposes only."
        })
        assert result.passed is True

    def test_passes_with_consult_professional(self) -> None:
        result = check_disclaimer_not_advice({
            "disclaimer": "Please consult a licensed professional before acting."
        })
        assert result.passed is True

    def test_fails_with_generic_text(self) -> None:
        result = check_disclaimer_not_advice({
            "disclaimer": "Welcome to our healthcare assistant platform."
        })
        assert result.passed is False

    def test_fails_with_missing_disclaimer(self) -> None:
        result = check_disclaimer_not_advice({})
        assert result.passed is False

    def test_severity_is_critical(self) -> None:
        result = check_disclaimer_not_advice({})
        assert result.severity == FindingSeverity.CRITICAL


# ---------------------------------------------------------------------------
# Security checks
# ---------------------------------------------------------------------------


class TestCheckInputValidation:
    def test_passes_when_declared(self) -> None:
        result = check_input_validation_declared({"input_validation": {"enabled": True}})
        assert result.passed is True

    def test_fails_when_missing(self) -> None:
        result = check_input_validation_declared({})
        assert result.passed is False

    def test_fails_when_false(self) -> None:
        result = check_input_validation_declared({"input_validation": False})
        assert result.passed is False

    def test_severity_is_high(self) -> None:
        result = check_input_validation_declared({})
        assert result.severity == FindingSeverity.HIGH


class TestCheckRateLimiting:
    def test_passes_when_declared(self) -> None:
        result = check_rate_limiting_declared({"rate_limiting": {"rpm": 60}})
        assert result.passed is True

    def test_fails_when_missing(self) -> None:
        result = check_rate_limiting_declared({})
        assert result.passed is False

    def test_severity_is_medium(self) -> None:
        result = check_rate_limiting_declared({})
        assert result.severity == FindingSeverity.MEDIUM


# ---------------------------------------------------------------------------
# Grounding checks
# ---------------------------------------------------------------------------


class TestCheckHasSources:
    def test_passes_with_one_source(self) -> None:
        result = check_has_sources({"sources": ["medline"]})
        assert result.passed is True

    def test_fails_with_empty_sources(self) -> None:
        result = check_has_sources({"sources": []})
        assert result.passed is False

    def test_fails_with_missing_sources(self) -> None:
        result = check_has_sources({})
        assert result.passed is False

    def test_fails_with_non_list(self) -> None:
        result = check_has_sources({"sources": "medline"})
        assert result.passed is False


# ---------------------------------------------------------------------------
# Governance checks
# ---------------------------------------------------------------------------


class TestCheckHumanReviewGate:
    def test_not_required_for_informational(self) -> None:
        result = check_human_review_gate({"risk_tier": "informational"})
        assert result.passed is True
        assert result.severity == FindingSeverity.INFO

    def test_not_required_for_advisory(self) -> None:
        result = check_human_review_gate({"risk_tier": "advisory"})
        assert result.passed is True

    def test_required_for_decision_support_present(self) -> None:
        result = check_human_review_gate({
            "risk_tier": "decision_support",
            "human_review_gate": {"enabled": True},
        })
        assert result.passed is True
        assert result.severity == FindingSeverity.CRITICAL

    def test_required_for_decision_support_missing(self) -> None:
        result = check_human_review_gate({"risk_tier": "decision_support"})
        assert result.passed is False
        assert result.severity == FindingSeverity.CRITICAL


class TestCheckAuditTrail:
    def test_passes_when_declared(self) -> None:
        result = check_audit_trail_declared({"audit_trail": {"enabled": True}})
        assert result.passed is True

    def test_fails_when_missing(self) -> None:
        result = check_audit_trail_declared({})
        assert result.passed is False


# ---------------------------------------------------------------------------
# run_automated_checks
# ---------------------------------------------------------------------------


class TestRunAutomatedChecks:
    def test_full_config_all_pass(self) -> None:
        config = _full_config()
        results = run_automated_checks(config)
        failed = [r for r in results if not r.passed]
        assert failed == [], f"Unexpected failures: {[r.check_id for r in failed]}"

    def test_empty_config_has_failures(self) -> None:
        results = run_automated_checks({})
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0

    def test_returns_one_result_per_check(self) -> None:
        config = _full_config()
        results = run_automated_checks(config)
        assert len(results) == len(DEFAULT_CHECKS)

    def test_custom_check_suite(self) -> None:
        results = run_automated_checks(
            {"domain": "finance"},
            checks=[check_has_domain],
        )
        assert len(results) == 1
        assert results[0].passed is True

    def test_check_ids_are_unique(self) -> None:
        config = _full_config()
        results = run_automated_checks(config)
        ids = [r.check_id for r in results]
        assert len(ids) == len(set(ids))

    def test_description_check_passes_with_long_text(self) -> None:
        result = check_has_description({
            "description": "This is a comprehensive healthcare assistant template."
        })
        assert result.passed is True

    def test_description_check_fails_with_short_text(self) -> None:
        result = check_has_description({"description": "Short"})
        assert result.passed is False
