"""Unit tests for certification.risk_tier module."""
from __future__ import annotations

import pytest

from agent_vertical.certification.risk_tier import RiskTier, risk_tier_for_domain


class TestRiskTierValues:
    """Verify enum members exist with correct string values."""

    def test_informational_value(self) -> None:
        assert RiskTier.INFORMATIONAL.value == "INFORMATIONAL"

    def test_advisory_value(self) -> None:
        assert RiskTier.ADVISORY.value == "ADVISORY"

    def test_decision_support_value(self) -> None:
        assert RiskTier.DECISION_SUPPORT.value == "DECISION_SUPPORT"

    def test_all_three_members_exist(self) -> None:
        members = list(RiskTier)
        assert len(members) == 3

    def test_is_str_enum(self) -> None:
        assert isinstance(RiskTier.INFORMATIONAL, str)

    def test_str_equality(self) -> None:
        assert RiskTier.INFORMATIONAL == "INFORMATIONAL"


class TestRiskTierOrdering:
    """Verify comparison operators follow INFORMATIONAL < ADVISORY < DECISION_SUPPORT."""

    def test_informational_less_than_advisory(self) -> None:
        assert RiskTier.INFORMATIONAL < RiskTier.ADVISORY

    def test_advisory_less_than_decision_support(self) -> None:
        assert RiskTier.ADVISORY < RiskTier.DECISION_SUPPORT

    def test_informational_less_than_decision_support(self) -> None:
        assert RiskTier.INFORMATIONAL < RiskTier.DECISION_SUPPORT

    def test_decision_support_greater_than_informational(self) -> None:
        assert RiskTier.DECISION_SUPPORT > RiskTier.INFORMATIONAL

    def test_decision_support_greater_than_advisory(self) -> None:
        assert RiskTier.DECISION_SUPPORT > RiskTier.ADVISORY

    def test_advisory_greater_than_informational(self) -> None:
        assert RiskTier.ADVISORY > RiskTier.INFORMATIONAL

    def test_equal_tiers_le(self) -> None:
        assert RiskTier.ADVISORY <= RiskTier.ADVISORY

    def test_equal_tiers_ge(self) -> None:
        assert RiskTier.DECISION_SUPPORT >= RiskTier.DECISION_SUPPORT

    def test_less_than_returns_not_implemented_for_non_tier(self) -> None:
        result = RiskTier.INFORMATIONAL.__lt__("not_a_tier")
        assert result is NotImplemented

    def test_greater_than_returns_not_implemented_for_non_tier(self) -> None:
        result = RiskTier.ADVISORY.__gt__(42)
        assert result is NotImplemented

    def test_le_returns_not_implemented_for_non_tier(self) -> None:
        result = RiskTier.INFORMATIONAL.__le__("not_a_tier")
        assert result is NotImplemented

    def test_ge_returns_not_implemented_for_non_tier(self) -> None:
        result = RiskTier.ADVISORY.__ge__(42)
        assert result is NotImplemented

    def test_sorted_produces_correct_order(self) -> None:
        tiers = [RiskTier.DECISION_SUPPORT, RiskTier.INFORMATIONAL, RiskTier.ADVISORY]
        assert sorted(tiers) == [
            RiskTier.INFORMATIONAL,
            RiskTier.ADVISORY,
            RiskTier.DECISION_SUPPORT,
        ]


class TestRiskTierMinimumPassingScore:
    """Verify minimum_passing_score property returns the correct threshold."""

    def test_informational_minimum_score(self) -> None:
        assert RiskTier.INFORMATIONAL.minimum_passing_score == 60

    def test_advisory_minimum_score(self) -> None:
        assert RiskTier.ADVISORY.minimum_passing_score == 75

    def test_decision_support_minimum_score(self) -> None:
        assert RiskTier.DECISION_SUPPORT.minimum_passing_score == 90

    def test_scores_increase_with_tier(self) -> None:
        assert (
            RiskTier.INFORMATIONAL.minimum_passing_score
            < RiskTier.ADVISORY.minimum_passing_score
            < RiskTier.DECISION_SUPPORT.minimum_passing_score
        )


class TestRiskTierRequiresHumanReview:
    """Verify requires_human_review property."""

    def test_informational_does_not_require_human_review(self) -> None:
        assert RiskTier.INFORMATIONAL.requires_human_review is False

    def test_advisory_requires_human_review(self) -> None:
        assert RiskTier.ADVISORY.requires_human_review is True

    def test_decision_support_requires_human_review(self) -> None:
        assert RiskTier.DECISION_SUPPORT.requires_human_review is True


class TestRiskTierRequiresAuditTrail:
    """Verify requires_audit_trail property."""

    def test_informational_does_not_require_audit_trail(self) -> None:
        assert RiskTier.INFORMATIONAL.requires_audit_trail is False

    def test_advisory_requires_audit_trail(self) -> None:
        assert RiskTier.ADVISORY.requires_audit_trail is True

    def test_decision_support_requires_audit_trail(self) -> None:
        assert RiskTier.DECISION_SUPPORT.requires_audit_trail is True


class TestRiskTierRequiresExplainability:
    """Verify requires_explainability property."""

    def test_informational_does_not_require_explainability(self) -> None:
        assert RiskTier.INFORMATIONAL.requires_explainability is False

    def test_advisory_does_not_require_explainability(self) -> None:
        assert RiskTier.ADVISORY.requires_explainability is False

    def test_decision_support_requires_explainability(self) -> None:
        assert RiskTier.DECISION_SUPPORT.requires_explainability is True


class TestRiskTierForDomain:
    """Verify risk_tier_for_domain returns correct defaults."""

    def test_healthcare_returns_decision_support(self) -> None:
        assert risk_tier_for_domain("healthcare") == RiskTier.DECISION_SUPPORT

    def test_medical_returns_decision_support(self) -> None:
        assert risk_tier_for_domain("medical") == RiskTier.DECISION_SUPPORT

    def test_finance_returns_advisory(self) -> None:
        assert risk_tier_for_domain("finance") == RiskTier.ADVISORY

    def test_legal_returns_advisory(self) -> None:
        assert risk_tier_for_domain("legal") == RiskTier.ADVISORY

    def test_education_returns_advisory(self) -> None:
        assert risk_tier_for_domain("education") == RiskTier.ADVISORY

    def test_tutoring_returns_informational(self) -> None:
        assert risk_tier_for_domain("tutoring") == RiskTier.INFORMATIONAL

    def test_faq_returns_informational(self) -> None:
        assert risk_tier_for_domain("faq") == RiskTier.INFORMATIONAL

    def test_unknown_domain_defaults_to_advisory(self) -> None:
        assert risk_tier_for_domain("unknown_domain_xyz") == RiskTier.ADVISORY

    def test_case_insensitive_lookup(self) -> None:
        assert risk_tier_for_domain("HEALTHCARE") == RiskTier.DECISION_SUPPORT

    def test_whitespace_stripped_in_lookup(self) -> None:
        assert risk_tier_for_domain("  finance  ") == RiskTier.ADVISORY

    def test_underwriting_returns_decision_support(self) -> None:
        assert risk_tier_for_domain("underwriting") == RiskTier.DECISION_SUPPORT
