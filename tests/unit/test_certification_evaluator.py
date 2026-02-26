"""Tests for CertificationEvaluator and certification requirements."""
from __future__ import annotations

import pytest

from agent_vertical.certification.evaluator import (
    CertificationEvaluator,
    CertificationFinding,
    CertificationResult,
)
from agent_vertical.certification.requirements import (
    CertificationRequirement,
    RequirementSet,
    get_requirements,
)
from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.certification.scorer import (
    CheckResult,
    CertificationScorer,
    FindingSeverity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_check_result(
    check_id: str = "check.001",
    check_name: str = "Test Check",
    passed: bool = True,
    severity: FindingSeverity = FindingSeverity.HIGH,
    description: str = "A test check",
    detail: str = "",
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        check_name=check_name,
        passed=passed,
        severity=severity,
        description=description,
        detail=detail,
    )


@pytest.fixture()
def evaluator() -> CertificationEvaluator:
    return CertificationEvaluator("healthcare", RiskTier.ADVISORY)


# ---------------------------------------------------------------------------
# CertificationEvaluator construction
# ---------------------------------------------------------------------------

class TestCertificationEvaluatorConstruction:
    def test_default_scorer_used(self) -> None:
        evaluator = CertificationEvaluator("healthcare", RiskTier.INFORMATIONAL)
        assert evaluator._scorer is not None

    def test_custom_scorer_used(self) -> None:
        custom_scorer = CertificationScorer()
        evaluator = CertificationEvaluator(
            "healthcare", RiskTier.INFORMATIONAL, scorer=custom_scorer
        )
        assert evaluator._scorer is custom_scorer

    def test_domain_stored(self) -> None:
        evaluator = CertificationEvaluator("finance", RiskTier.INFORMATIONAL)
        assert evaluator._domain == "finance"

    def test_tier_stored(self) -> None:
        evaluator = CertificationEvaluator("finance", RiskTier.DECISION_SUPPORT)
        assert evaluator._tier == RiskTier.DECISION_SUPPORT


# ---------------------------------------------------------------------------
# CertificationEvaluator.evaluate — basic
# ---------------------------------------------------------------------------

class TestCertificationEvaluatorEvaluate:
    def test_evaluate_empty_checks_passes(
        self, evaluator: CertificationEvaluator
    ) -> None:
        result = evaluator.evaluate([])
        assert isinstance(result, CertificationResult)
        assert result.score == 100
        assert result.passed is True

    def test_evaluate_all_passing_checks(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [
            _make_check_result("c1", passed=True, severity=FindingSeverity.HIGH),
            _make_check_result("c2", passed=True, severity=FindingSeverity.MEDIUM),
        ]
        result = evaluator.evaluate(checks)
        assert result.score == 100
        assert result.passed is True

    def test_evaluate_domain_in_result(
        self, evaluator: CertificationEvaluator
    ) -> None:
        result = evaluator.evaluate([])
        assert result.domain == "healthcare"

    def test_evaluate_tier_in_result(
        self, evaluator: CertificationEvaluator
    ) -> None:
        result = evaluator.evaluate([])
        assert result.tier == RiskTier.ADVISORY

    def test_evaluate_findings_populated(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [_make_check_result("c1", passed=True)]
        result = evaluator.evaluate(checks)
        assert len(result.findings) == 1

    def test_evaluate_failed_findings_populated(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [
            _make_check_result("c1", passed=False, severity=FindingSeverity.CRITICAL),
            _make_check_result("c2", passed=True),
        ]
        result = evaluator.evaluate(checks)
        assert len(result.failed_findings) == 1

    def test_evaluate_critical_findings_populated(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [
            _make_check_result("c1", passed=False, severity=FindingSeverity.CRITICAL),
            _make_check_result("c2", passed=False, severity=FindingSeverity.HIGH),
        ]
        result = evaluator.evaluate(checks)
        assert len(result.critical_findings) == 1

    def test_evaluate_passed_check_message_format(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [_make_check_result("c1", check_name="PHI Check", passed=True)]
        result = evaluator.evaluate(checks)
        assert "PASSED" in result.findings[0].message

    def test_evaluate_failed_check_message_format(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [_make_check_result("c1", check_name="PHI Check", passed=False)]
        result = evaluator.evaluate(checks)
        assert "FAILED" in result.findings[0].message

    def test_evaluate_failed_check_has_remediation(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [_make_check_result("c1", passed=False, severity=FindingSeverity.CRITICAL)]
        result = evaluator.evaluate(checks)
        assert len(result.failed_findings[0].remediation) > 0

    def test_evaluate_passed_check_no_remediation(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [_make_check_result("c1", passed=True)]
        result = evaluator.evaluate(checks)
        assert result.findings[0].remediation == ""

    def test_evaluate_passes_when_score_meets_tier_minimum(self) -> None:
        # INFORMATIONAL tier has minimum 60
        evaluator = CertificationEvaluator("healthcare", RiskTier.INFORMATIONAL)
        # Pass all checks to get score 100
        checks = [_make_check_result("c1", passed=True, severity=FindingSeverity.INFO)]
        result = evaluator.evaluate(checks)
        assert result.passed is True

    def test_evaluate_fails_when_score_below_tier_minimum(self) -> None:
        # Use a tier with higher minimum
        evaluator = CertificationEvaluator("healthcare", RiskTier.DECISION_SUPPORT)
        # Fail multiple critical checks
        checks = [
            _make_check_result(f"c{i}", passed=False, severity=FindingSeverity.CRITICAL)
            for i in range(5)
        ]
        result = evaluator.evaluate(checks)
        assert result.passed is False

    def test_evaluate_with_detail_in_failed_check(
        self, evaluator: CertificationEvaluator
    ) -> None:
        checks = [
            _make_check_result("c1", passed=False, detail="Specific failure detail")
        ]
        result = evaluator.evaluate(checks)
        assert "Specific failure detail" in result.findings[0].message


# ---------------------------------------------------------------------------
# CertificationEvaluator._remediation_for
# ---------------------------------------------------------------------------

class TestRemediationFor:
    def test_critical_remediation(self) -> None:
        check = _make_check_result("c1", passed=False, severity=FindingSeverity.CRITICAL)
        hint = CertificationEvaluator._remediation_for(check)
        assert "immediately" in hint.lower() or "halt" in hint.lower()

    def test_high_remediation(self) -> None:
        check = _make_check_result("c1", passed=False, severity=FindingSeverity.HIGH)
        hint = CertificationEvaluator._remediation_for(check)
        assert len(hint) > 0

    def test_medium_remediation(self) -> None:
        check = _make_check_result("c1", passed=False, severity=FindingSeverity.MEDIUM)
        hint = CertificationEvaluator._remediation_for(check)
        assert len(hint) > 0

    def test_low_remediation(self) -> None:
        check = _make_check_result("c1", passed=False, severity=FindingSeverity.LOW)
        hint = CertificationEvaluator._remediation_for(check)
        assert "backlog" in hint.lower()

    def test_info_remediation(self) -> None:
        check = _make_check_result("c1", passed=False, severity=FindingSeverity.INFO)
        hint = CertificationEvaluator._remediation_for(check)
        assert len(hint) > 0


# ---------------------------------------------------------------------------
# CertificationRequirement
# ---------------------------------------------------------------------------

class TestCertificationRequirement:
    def test_applies_to_matching_tier(self) -> None:
        req = CertificationRequirement(
            requirement_id="test.req",
            name="Test",
            description="desc",
            severity=FindingSeverity.HIGH,
            domain="healthcare",
            risk_tiers=frozenset({RiskTier.ADVISORY, RiskTier.DECISION_SUPPORT}),
        )
        assert req.applies_to(RiskTier.ADVISORY) is True

    def test_does_not_apply_to_non_matching_tier(self) -> None:
        req = CertificationRequirement(
            requirement_id="test.req",
            name="Test",
            description="desc",
            severity=FindingSeverity.HIGH,
            domain="healthcare",
            risk_tiers=frozenset({RiskTier.DECISION_SUPPORT}),
        )
        assert req.applies_to(RiskTier.INFORMATIONAL) is False

    def test_default_rationale_empty(self) -> None:
        req = CertificationRequirement(
            requirement_id="test.req",
            name="Test",
            description="desc",
            severity=FindingSeverity.HIGH,
            domain="healthcare",
            risk_tiers=frozenset({RiskTier.INFORMATIONAL}),
        )
        assert req.rationale == ""

    def test_frozen_dataclass(self) -> None:
        req = CertificationRequirement(
            requirement_id="test.req",
            name="Test",
            description="desc",
            severity=FindingSeverity.HIGH,
            domain="healthcare",
            risk_tiers=frozenset({RiskTier.INFORMATIONAL}),
        )
        with pytest.raises((AttributeError, TypeError)):
            req.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RequirementSet
# ---------------------------------------------------------------------------

class TestRequirementSet:
    def _make_req(
        self,
        req_id: str,
        severity: FindingSeverity,
        tiers: frozenset[RiskTier],
    ) -> CertificationRequirement:
        return CertificationRequirement(
            requirement_id=req_id,
            name=req_id,
            description="desc",
            severity=severity,
            domain="test",
            risk_tiers=tiers,
        )

    def test_critical_requirements(self) -> None:
        req_set = RequirementSet(
            domain="test",
            tier=RiskTier.INFORMATIONAL,
            requirements=[
                self._make_req("r1", FindingSeverity.CRITICAL, frozenset({RiskTier.INFORMATIONAL})),
                self._make_req("r2", FindingSeverity.HIGH, frozenset({RiskTier.INFORMATIONAL})),
            ],
        )
        critical = req_set.critical_requirements()
        assert len(critical) == 1
        assert critical[0].requirement_id == "r1"

    def test_mandatory_count(self) -> None:
        req_set = RequirementSet(
            domain="test",
            tier=RiskTier.ADVISORY,
            requirements=[
                self._make_req("r1", FindingSeverity.HIGH, frozenset({RiskTier.ADVISORY})),
                self._make_req("r2", FindingSeverity.MEDIUM, frozenset({RiskTier.ADVISORY})),
            ],
        )
        assert req_set.mandatory_count() == 2

    def test_empty_requirements(self) -> None:
        req_set = RequirementSet(domain="test", tier=RiskTier.INFORMATIONAL)
        assert req_set.mandatory_count() == 0
        assert req_set.critical_requirements() == []


# ---------------------------------------------------------------------------
# get_requirements
# ---------------------------------------------------------------------------

class TestGetRequirements:
    def test_healthcare_informational_has_requirements(self) -> None:
        req_set = get_requirements("healthcare", RiskTier.INFORMATIONAL)
        assert req_set.mandatory_count() > 0

    def test_healthcare_decision_support_has_more_requirements(self) -> None:
        info_set = get_requirements("healthcare", RiskTier.INFORMATIONAL)
        ds_set = get_requirements("healthcare", RiskTier.DECISION_SUPPORT)
        assert ds_set.mandatory_count() >= info_set.mandatory_count()

    def test_finance_requirements_exist(self) -> None:
        req_set = get_requirements("finance", RiskTier.ADVISORY)
        assert req_set.mandatory_count() > 0

    def test_legal_requirements_exist(self) -> None:
        req_set = get_requirements("legal", RiskTier.INFORMATIONAL)
        assert req_set.mandatory_count() > 0

    def test_education_requirements_exist(self) -> None:
        req_set = get_requirements("education", RiskTier.INFORMATIONAL)
        assert req_set.mandatory_count() > 0

    def test_unknown_domain_returns_generic_only(self) -> None:
        req_set = get_requirements("unknown_xyz_domain", RiskTier.INFORMATIONAL)
        # Should still return a RequirementSet (generic requirements)
        assert isinstance(req_set, RequirementSet)

    def test_all_requirements_apply_to_tier(self) -> None:
        req_set = get_requirements("healthcare", RiskTier.ADVISORY)
        for req in req_set.requirements:
            assert req.applies_to(RiskTier.ADVISORY)

    def test_domain_case_insensitive(self) -> None:
        lower = get_requirements("healthcare", RiskTier.INFORMATIONAL)
        upper = get_requirements("HEALTHCARE", RiskTier.INFORMATIONAL)
        assert lower.mandatory_count() == upper.mandatory_count()

    def test_alias_medical_same_as_healthcare(self) -> None:
        healthcare = get_requirements("healthcare", RiskTier.INFORMATIONAL)
        medical = get_requirements("medical", RiskTier.INFORMATIONAL)
        assert healthcare.mandatory_count() == medical.mandatory_count()
