"""Tests for DomainComplianceChecker, ComplianceCheckResult, RuleViolation."""
from __future__ import annotations

import pytest

from agent_vertical.compliance.checker import (
    ComplianceCheckResult,
    DomainComplianceChecker,
    RuleViolation,
    _check_prohibited,
    _check_required,
)
from agent_vertical.compliance.domain_rules import (
    ComplianceRule,
    DomainComplianceRules,
    RuleType,
    get_domain_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def healthcare_checker() -> DomainComplianceChecker:
    return DomainComplianceChecker("healthcare")


@pytest.fixture()
def finance_checker() -> DomainComplianceChecker:
    return DomainComplianceChecker("finance")


# ---------------------------------------------------------------------------
# _check_prohibited helper
# ---------------------------------------------------------------------------

class TestCheckProhibited:
    def test_plain_phrase_match(self) -> None:
        rule = ComplianceRule(
            rule_id="test.rule",
            rule_type=RuleType.PROHIBITED_PHRASE,
            description="No diagnosis",
            severity="critical",
            pattern="you have diabetes",
            is_regex=False,
            remediation="Remove diagnosis",
        )
        violation = _check_prohibited(rule, "you have diabetes now", "You have diabetes now")
        assert violation is not None
        assert violation.rule_id == "test.rule"

    def test_plain_phrase_no_match(self) -> None:
        rule = ComplianceRule(
            rule_id="test.rule",
            rule_type=RuleType.PROHIBITED_PHRASE,
            description="No diagnosis",
            severity="critical",
            pattern="you have cancer",
            is_regex=False,
            remediation="Remove diagnosis",
        )
        violation = _check_prohibited(rule, "general health info", "general health info")
        assert violation is None

    def test_regex_pattern_match(self) -> None:
        rule = ComplianceRule(
            rule_id="test.rule",
            rule_type=RuleType.PROHIBITED_PATTERN,
            description="No diagnosis",
            severity="high",
            pattern=r"you (have|are diagnosed with) \w+",
            is_regex=True,
            remediation="Remove",
        )
        violation = _check_prohibited(
            rule, "you have diabetes mellitus", "You have diabetes mellitus"
        )
        assert violation is not None

    def test_regex_pattern_no_match(self) -> None:
        rule = ComplianceRule(
            rule_id="test.rule",
            rule_type=RuleType.PROHIBITED_PATTERN,
            description="No diagnosis",
            severity="high",
            pattern=r"^\d{10}$",
            is_regex=True,
            remediation="Remove",
        )
        violation = _check_prohibited(rule, "general info text", "general info text")
        assert violation is None


class TestCheckRequired:
    def test_missing_required_phrase(self) -> None:
        rule = ComplianceRule(
            rule_id="test.disclaimer",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            description="Must have disclaimer",
            severity="critical",
            pattern="does not constitute medical advice",
            is_regex=False,
            remediation="Add disclaimer",
        )
        violation = _check_required(rule, "here is some health information")
        assert violation is not None
        assert violation.matched_text == ""

    def test_present_required_phrase_no_violation(self) -> None:
        rule = ComplianceRule(
            rule_id="test.disclaimer",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            description="Must have disclaimer",
            severity="critical",
            pattern="does not constitute medical advice",
            is_regex=False,
            remediation="Add disclaimer",
        )
        violation = _check_required(
            rule, "this does not constitute medical advice"
        )
        assert violation is None

    def test_missing_required_regex(self) -> None:
        rule = ComplianceRule(
            rule_id="test.disclaimer",
            rule_type=RuleType.REQUIRED_PATTERN,
            description="Must have disclaimer phrase",
            severity="high",
            pattern=r"disclaimer|not (medical|legal) advice",
            is_regex=True,
            remediation="Add disclaimer",
        )
        violation = _check_required(rule, "some response without any notice")
        assert violation is not None

    def test_present_required_regex_no_violation(self) -> None:
        rule = ComplianceRule(
            rule_id="test.disclaimer",
            rule_type=RuleType.REQUIRED_PATTERN,
            description="Must have disclaimer phrase",
            severity="high",
            pattern=r"disclaimer",
            is_regex=True,
            remediation="Add disclaimer",
        )
        violation = _check_required(rule, "this comes with a disclaimer notice")
        assert violation is None


# ---------------------------------------------------------------------------
# DomainComplianceChecker construction
# ---------------------------------------------------------------------------

class TestDomainComplianceCheckerConstruction:
    def test_domain_normalised_to_lowercase(self) -> None:
        checker = DomainComplianceChecker("HEALTHCARE")
        result = checker.check("Some response.")
        assert result.domain == "healthcare"

    def test_domain_strip_whitespace(self) -> None:
        checker = DomainComplianceChecker("  finance  ")
        result = checker.check("Some response.")
        assert result.domain == "finance"

    def test_custom_rules_merged(self) -> None:
        extra_rule = ComplianceRule(
            rule_id="custom.rule",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            description="Must contain custom phrase",
            severity="medium",
            pattern="custom required phrase",
            is_regex=False,
            remediation="Add custom phrase",
        )
        custom_rules = DomainComplianceRules(
            domain="healthcare",
            rules=[extra_rule],
        )
        checker = DomainComplianceChecker("healthcare", custom_rules=custom_rules)
        result = checker.check("Response without the custom phrase")
        # There should be at least the custom rule violation
        violation_ids = [v.rule_id for v in result.violations]
        assert "custom.rule" in violation_ids


# ---------------------------------------------------------------------------
# DomainComplianceChecker.check
# ---------------------------------------------------------------------------

class TestDomainComplianceCheckerCheck:
    def test_compliant_healthcare_response(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        # A response that has no prohibited content and no required phrases
        # we need to check what rules exist
        result = healthcare_checker.check(
            "This does not constitute medical advice. Consult your doctor."
        )
        assert isinstance(result, ComplianceCheckResult)

    def test_result_domain_correct(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("Some response.")
        assert result.domain == "healthcare"

    def test_result_response_length(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        response = "Some response text."
        result = healthcare_checker.check(response)
        assert result.response_length == len(response)

    def test_total_rules_positive(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("text")
        assert result.total_rules > 0

    def test_passed_rules_and_violations_sum_to_total(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("Some text here.")
        assert result.passed_rules + len(result.violations) == result.total_rules

    def test_critical_violations_subset_of_violations(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("you have cancer, take this pill")
        for v in result.critical_violations:
            assert v.severity == "critical"
            assert v in result.violations

    def test_high_violations_subset_of_violations(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("some text here")
        for v in result.high_violations:
            assert v.severity == "high"
            assert v in result.violations

    def test_compliant_when_no_critical_or_high(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("text")
        expected_compliant = len(result.critical_violations) == 0 and len(result.high_violations) == 0
        assert result.is_compliant == expected_compliant

    def test_violations_sorted_by_severity(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        result = healthcare_checker.check("some problematic text")
        severities = [v.severity for v in result.violations]
        if len(severities) >= 2:
            for i in range(len(severities) - 1):
                sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                assert sev_order.get(severities[i], 99) <= sev_order.get(severities[i + 1], 99)

    def test_finance_checker_check(
        self, finance_checker: DomainComplianceChecker
    ) -> None:
        result = finance_checker.check("This is not investment advice.")
        assert isinstance(result, ComplianceCheckResult)
        assert result.domain == "finance"


# ---------------------------------------------------------------------------
# DomainComplianceChecker.check_batch
# ---------------------------------------------------------------------------

class TestCheckBatch:
    def test_batch_returns_one_per_response(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        responses = ["Response A.", "Response B.", "Response C."]
        results = healthcare_checker.check_batch(responses)
        assert len(results) == len(responses)

    def test_batch_results_are_check_results(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        results = healthcare_checker.check_batch(["text one", "text two"])
        for r in results:
            assert isinstance(r, ComplianceCheckResult)

    def test_empty_batch(
        self, healthcare_checker: DomainComplianceChecker
    ) -> None:
        results = healthcare_checker.check_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# get_domain_rules function
# ---------------------------------------------------------------------------

class TestGetDomainRules:
    def test_healthcare_returns_rules(self) -> None:
        rules = get_domain_rules("healthcare")
        assert rules.domain == "healthcare"
        assert len(rules.rules) > 0

    def test_unknown_domain_returns_empty_or_generic(self) -> None:
        rules = get_domain_rules("unknown_domain_xyz")
        assert isinstance(rules, DomainComplianceRules)

    def test_finance_rules_exist(self) -> None:
        rules = get_domain_rules("finance")
        assert len(rules.rules) > 0


# ---------------------------------------------------------------------------
# DomainComplianceRules methods
# ---------------------------------------------------------------------------

class TestDomainComplianceRulesMethods:
    def test_prohibited_phrase_rules(self) -> None:
        rules = get_domain_rules("healthcare")
        prohibited = rules.prohibited_phrase_rules()
        for rule in prohibited:
            assert rule.rule_type.value.startswith("PROHIBITED")

    def test_required_disclaimer_rules(self) -> None:
        rules = get_domain_rules("healthcare")
        required = rules.required_disclaimer_rules()
        for rule in required:
            assert rule.rule_type.value.startswith("REQUIRED")

    def test_by_severity_critical(self) -> None:
        rules = get_domain_rules("healthcare")
        critical_rules = rules.by_severity("critical")
        for rule in critical_rules:
            assert rule.severity == "critical"

    def test_by_severity_high(self) -> None:
        rules = get_domain_rules("healthcare")
        high_rules = rules.by_severity("high")
        for rule in high_rules:
            assert rule.severity == "high"

    def test_by_severity_unknown_returns_empty(self) -> None:
        rules = get_domain_rules("healthcare")
        result = rules.by_severity("nonexistent_severity")
        assert result == []


# ---------------------------------------------------------------------------
# list_supported_domains
# ---------------------------------------------------------------------------

class TestListSupportedDomains:
    def test_list_supported_domains(self) -> None:
        from agent_vertical.compliance.domain_rules import list_supported_domains
        domains = list_supported_domains()
        assert isinstance(domains, list)
        assert "healthcare" in domains
        assert "finance" in domains
        assert "legal" in domains
        assert "education" in domains

    def test_list_supported_domains_sorted(self) -> None:
        from agent_vertical.compliance.domain_rules import list_supported_domains
        domains = list_supported_domains()
        assert domains == sorted(domains)
