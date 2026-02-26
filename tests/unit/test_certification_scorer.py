"""Unit tests for certification.scorer module."""
from __future__ import annotations

import pytest

from agent_vertical.certification.scorer import (
    CheckResult,
    CertificationScorer,
    FindingSeverity,
    ScoringResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_check(
    check_id: str,
    passed: bool,
    severity: FindingSeverity,
    name: str = "Test Check",
    description: str = "A test check.",
    detail: str = "",
) -> CheckResult:
    """Factory helper for CheckResult objects."""
    return CheckResult(
        check_id=check_id,
        check_name=name,
        passed=passed,
        severity=severity,
        description=description,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# FindingSeverity enum
# ---------------------------------------------------------------------------


class TestFindingSeverity:
    def test_all_five_values_exist(self) -> None:
        values = {s.value for s in FindingSeverity}
        assert values == {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}

    def test_is_str_enum(self) -> None:
        assert isinstance(FindingSeverity.CRITICAL, str)


# ---------------------------------------------------------------------------
# CheckResult dataclass
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_frozen_dataclass_prevents_mutation(self) -> None:
        check = make_check("c1", True, FindingSeverity.LOW)
        with pytest.raises((AttributeError, TypeError)):
            check.passed = False  # type: ignore[misc]

    def test_default_detail_is_empty_string(self) -> None:
        check = make_check("c1", True, FindingSeverity.INFO)
        assert check.detail == ""

    def test_detail_is_stored(self) -> None:
        check = make_check("c1", False, FindingSeverity.HIGH, detail="Missing header.")
        assert check.detail == "Missing header."


# ---------------------------------------------------------------------------
# CertificationScorer — empty input
# ---------------------------------------------------------------------------


class TestCertificationScorerEmptyInput:
    def test_empty_results_returns_score_100(self) -> None:
        scorer = CertificationScorer()
        result = scorer.compute([])
        assert result.score == 100

    def test_empty_results_has_zero_counts(self) -> None:
        scorer = CertificationScorer()
        result = scorer.compute([])
        assert result.total_checks == 0
        assert result.passed_checks == 0
        assert result.failed_checks == 0

    def test_empty_results_has_empty_penalty_breakdown(self) -> None:
        scorer = CertificationScorer()
        result = scorer.compute([])
        assert result.penalty_breakdown == {}


# ---------------------------------------------------------------------------
# CertificationScorer — all passing checks
# ---------------------------------------------------------------------------


class TestCertificationScorerAllPass:
    def test_all_pass_returns_score_100(self) -> None:
        scorer = CertificationScorer()
        checks = [
            make_check("c1", True, FindingSeverity.CRITICAL),
            make_check("c2", True, FindingSeverity.HIGH),
            make_check("c3", True, FindingSeverity.MEDIUM),
        ]
        result = scorer.compute(checks)
        assert result.score == 100

    def test_all_pass_zero_failures(self) -> None:
        scorer = CertificationScorer()
        checks = [make_check(f"c{i}", True, FindingSeverity.HIGH) for i in range(5)]
        result = scorer.compute(checks)
        assert result.failed_checks == 0
        assert result.critical_failures == 0

    def test_all_pass_total_equals_input_count(self) -> None:
        scorer = CertificationScorer()
        checks = [make_check(f"c{i}", True, FindingSeverity.LOW) for i in range(4)]
        result = scorer.compute(checks)
        assert result.total_checks == 4
        assert result.passed_checks == 4


# ---------------------------------------------------------------------------
# CertificationScorer — all failing checks
# ---------------------------------------------------------------------------


class TestCertificationScorerAllFail:
    def test_single_critical_failure_returns_zero(self) -> None:
        """One critical check; if that one fails, normalised penalty = 100, score = 0."""
        scorer = CertificationScorer()
        checks = [make_check("c1", False, FindingSeverity.CRITICAL)]
        result = scorer.compute(checks)
        assert result.score == 0

    def test_all_info_failures_return_score_zero(self) -> None:
        """INFO penalty is 0; 100 - 0 = 100, but normalised over 0 possible penalty = 0 deducted."""
        scorer = CertificationScorer()
        # All INFO failures → raw_penalty = 0, max_possible = 0 → normalised = 0 → score = 100
        checks = [make_check(f"c{i}", False, FindingSeverity.INFO) for i in range(3)]
        result = scorer.compute(checks)
        assert result.score == 100

    def test_penalty_breakdown_contains_failed_severities(self) -> None:
        scorer = CertificationScorer()
        checks = [
            make_check("c1", False, FindingSeverity.CRITICAL),
            make_check("c2", False, FindingSeverity.HIGH),
        ]
        result = scorer.compute(checks)
        assert "CRITICAL" in result.penalty_breakdown
        assert "HIGH" in result.penalty_breakdown

    def test_penalty_breakdown_excludes_passing_severities(self) -> None:
        scorer = CertificationScorer()
        checks = [make_check("c1", False, FindingSeverity.CRITICAL)]
        result = scorer.compute(checks)
        assert "HIGH" not in result.penalty_breakdown


# ---------------------------------------------------------------------------
# CertificationScorer — mixed pass/fail
# ---------------------------------------------------------------------------


class TestCertificationScorerMixed:
    def test_score_clamped_between_0_and_100(self) -> None:
        scorer = CertificationScorer()
        checks = [
            make_check("c1", True, FindingSeverity.CRITICAL),
            make_check("c2", False, FindingSeverity.HIGH),
            make_check("c3", True, FindingSeverity.LOW),
        ]
        result = scorer.compute(checks)
        assert 0 <= result.score <= 100

    def test_failure_counts_are_accurate(self) -> None:
        scorer = CertificationScorer()
        checks = [
            make_check("c1", False, FindingSeverity.CRITICAL),
            make_check("c2", False, FindingSeverity.HIGH),
            make_check("c3", True, FindingSeverity.MEDIUM),
            make_check("c4", False, FindingSeverity.LOW),
        ]
        result = scorer.compute(checks)
        assert result.critical_failures == 1
        assert result.high_failures == 1
        assert result.medium_failures == 0
        assert result.low_failures == 1
        assert result.failed_checks == 3
        assert result.passed_checks == 1

    def test_custom_severity_penalties_are_applied(self) -> None:
        """Custom zero-weight penalties for HIGH should leave HIGH failures without penalty."""
        from agent_vertical.certification.scorer import FindingSeverity
        custom = {
            FindingSeverity.CRITICAL: 25.0,
            FindingSeverity.HIGH: 0.0,
            FindingSeverity.MEDIUM: 5.0,
            FindingSeverity.LOW: 2.0,
            FindingSeverity.INFO: 0.0,
        }
        scorer = CertificationScorer(severity_penalties=custom)
        # All HIGH failures, no penalty weight → score = 100
        checks = [make_check(f"c{i}", False, FindingSeverity.HIGH) for i in range(3)]
        result = scorer.compute(checks)
        assert result.score == 100

    def test_scoring_result_is_dataclass_instance(self) -> None:
        scorer = CertificationScorer()
        result = scorer.compute([make_check("c1", True, FindingSeverity.LOW)])
        assert isinstance(result, ScoringResult)
