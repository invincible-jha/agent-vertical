"""Tests for CertificationReporter."""
from __future__ import annotations

import json

import pytest

from agent_vertical.certification.evaluator import CertificationFinding, CertificationResult
from agent_vertical.certification.report import CertificationReporter, _escape
from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.certification.scorer import FindingSeverity, ScoringResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_scoring_result(
    total: int = 10,
    passed: int = 8,
    failed: int = 2,
    critical: int = 1,
    high: int = 1,
) -> ScoringResult:
    return ScoringResult(
        score=75,
        total_checks=total,
        passed_checks=passed,
        failed_checks=failed,
        critical_failures=critical,
        high_failures=high,
        medium_failures=0,
        low_failures=0,
        penalty_breakdown={"CRITICAL": 40.0, "HIGH": 20.0},
    )


def _make_finding(
    check_id: str = "check.test",
    severity: FindingSeverity = FindingSeverity.HIGH,
    message: str = "Test issue",
    remediation: str = "Fix it",
) -> CertificationFinding:
    return CertificationFinding(
        check_id=check_id,
        severity=severity,
        message=message,
        remediation=remediation,
    )


def _make_result(
    domain: str = "healthcare",
    score: int = 75,
    passed: bool = True,
    findings: list[CertificationFinding] | None = None,
    failed_findings: list[CertificationFinding] | None = None,
    critical_findings: list[CertificationFinding] | None = None,
) -> CertificationResult:
    tier = RiskTier.ADVISORY
    sd = _make_scoring_result()
    return CertificationResult(
        domain=domain,
        tier=tier,
        score=score,
        passed=passed,
        scoring_detail=sd,
        findings=findings or [],
        failed_findings=failed_findings or [],
        critical_findings=critical_findings or [],
    )


@pytest.fixture()
def passing_result() -> CertificationResult:
    return _make_result(score=85, passed=True)


@pytest.fixture()
def failing_result() -> CertificationResult:
    critical = _make_finding("phi.leakage", FindingSeverity.CRITICAL, "PHI exposed", "Remove PHI")
    high = _make_finding("disclaimer.missing", FindingSeverity.HIGH, "No disclaimer", "Add disclaimer")
    info = _make_finding("info.note", FindingSeverity.INFO, "Info note", "N/A")
    return _make_result(
        score=55,
        passed=False,
        findings=[critical, high, info],
        failed_findings=[critical, high],
        critical_findings=[critical],
    )


@pytest.fixture()
def passing_reporter(passing_result: CertificationResult) -> CertificationReporter:
    return CertificationReporter(passing_result, agent_name="TestAgent v1")


@pytest.fixture()
def failing_reporter(failing_result: CertificationResult) -> CertificationReporter:
    return CertificationReporter(failing_result, agent_name="FailAgent v1")


# ---------------------------------------------------------------------------
# _escape helper
# ---------------------------------------------------------------------------

class TestEscape:
    def test_ampersand(self) -> None:
        assert _escape("a & b") == "a &amp; b"

    def test_less_than(self) -> None:
        assert _escape("a < b") == "a &lt; b"

    def test_greater_than(self) -> None:
        assert _escape("a > b") == "a &gt; b"

    def test_quote(self) -> None:
        assert _escape('a "b"') == "a &quot;b&quot;"

    def test_no_special_chars(self) -> None:
        assert _escape("plain text") == "plain text"

    def test_multiple_special_chars(self) -> None:
        result = _escape('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;" in result


# ---------------------------------------------------------------------------
# CertificationReporter.as_json
# ---------------------------------------------------------------------------

class TestAsJson:
    def test_returns_valid_json(self, passing_reporter: CertificationReporter) -> None:
        output = passing_reporter.as_json()
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_contains_required_keys(
        self, passing_reporter: CertificationReporter
    ) -> None:
        parsed = json.loads(passing_reporter.as_json())
        for key in ("report_version", "generated_at", "agent_name", "domain", "score", "passed"):
            assert key in parsed

    def test_json_agent_name(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert parsed["agent_name"] == "TestAgent v1"

    def test_json_score(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert parsed["score"] == 85

    def test_json_passed_true(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert parsed["passed"] is True

    def test_json_passed_false(self, failing_reporter: CertificationReporter) -> None:
        parsed = json.loads(failing_reporter.as_json())
        assert parsed["passed"] is False

    def test_json_findings_list(self, failing_reporter: CertificationReporter) -> None:
        parsed = json.loads(failing_reporter.as_json())
        assert isinstance(parsed["findings"], list)

    def test_json_critical_findings(self, failing_reporter: CertificationReporter) -> None:
        parsed = json.loads(failing_reporter.as_json())
        critical = parsed["critical_findings"]
        assert len(critical) >= 1

    def test_json_summary_has_checks(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        summary = parsed["summary"]
        assert "total_checks" in summary
        assert "passed_checks" in summary

    def test_json_custom_indent(self, passing_reporter: CertificationReporter) -> None:
        output = passing_reporter.as_json(indent=4)
        lines = output.split("\n")
        indented = [line for line in lines if line.startswith("    ")]
        assert len(indented) > 0

    def test_json_has_risk_tier(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert "risk_tier" in parsed

    def test_json_domain_correct(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert parsed["domain"] == "healthcare"

    def test_json_summary_penalty_breakdown(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert "penalty_breakdown" in parsed["summary"]


# ---------------------------------------------------------------------------
# CertificationReporter.as_text
# ---------------------------------------------------------------------------

class TestAsText:
    def test_returns_string(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert isinstance(text, str)

    def test_contains_agent_name(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "TestAgent v1" in text

    def test_contains_domain(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "healthcare" in text

    def test_contains_passed_verdict(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "PASSED" in text

    def test_contains_failed_verdict(self, failing_reporter: CertificationReporter) -> None:
        text = failing_reporter.as_text()
        assert "FAILED" in text

    def test_contains_score(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "85" in text

    def test_failed_findings_section(self, failing_reporter: CertificationReporter) -> None:
        text = failing_reporter.as_text()
        assert "FAILED FINDINGS" in text

    def test_no_failed_findings_no_section(
        self, passing_reporter: CertificationReporter
    ) -> None:
        text = passing_reporter.as_text()
        assert "FAILED FINDINGS" not in text

    def test_critical_shown_when_present(self, failing_reporter: CertificationReporter) -> None:
        text = failing_reporter.as_text()
        assert "CRITICAL" in text

    def test_separator_lines_present(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "=" * 10 in text

    def test_check_summary_section_present(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "CHECK SUMMARY" in text

    def test_total_checks_shown(self, passing_reporter: CertificationReporter) -> None:
        text = passing_reporter.as_text()
        assert "Total checks" in text

    def test_failing_reporter_agent_name(self, failing_reporter: CertificationReporter) -> None:
        text = failing_reporter.as_text()
        assert "FailAgent v1" in text

    def test_medium_failures_shown_in_text(self) -> None:
        sd = ScoringResult(
            score=60,
            total_checks=5,
            passed_checks=3,
            failed_checks=2,
            critical_failures=0,
            high_failures=0,
            medium_failures=2,
            low_failures=0,
            penalty_breakdown={"MEDIUM": 10.0},
        )
        result = CertificationResult(
            domain="healthcare",
            tier=RiskTier.ADVISORY,
            score=60,
            passed=False,
            scoring_detail=sd,
            findings=[],
            failed_findings=[],
            critical_findings=[],
        )
        reporter = CertificationReporter(result, agent_name="Agent")
        text = reporter.as_text()
        assert "MEDIUM" in text

    def test_low_failures_shown_in_text(self) -> None:
        sd = ScoringResult(
            score=70,
            total_checks=5,
            passed_checks=4,
            failed_checks=1,
            critical_failures=0,
            high_failures=0,
            medium_failures=0,
            low_failures=1,
            penalty_breakdown={"LOW": 2.0},
        )
        result = CertificationResult(
            domain="healthcare",
            tier=RiskTier.ADVISORY,
            score=70,
            passed=True,
            scoring_detail=sd,
            findings=[],
            failed_findings=[],
            critical_findings=[],
        )
        reporter = CertificationReporter(result, agent_name="Agent")
        text = reporter.as_text()
        assert "LOW" in text


# ---------------------------------------------------------------------------
# CertificationReporter.as_html
# ---------------------------------------------------------------------------

class TestAsHtml:
    def test_returns_html_string(self, passing_reporter: CertificationReporter) -> None:
        html = passing_reporter.as_html()
        assert "<!DOCTYPE html>" in html

    def test_contains_agent_name(self, passing_reporter: CertificationReporter) -> None:
        html = passing_reporter.as_html()
        assert "TestAgent v1" in html

    def test_contains_passed_label_green(
        self, passing_reporter: CertificationReporter
    ) -> None:
        html = passing_reporter.as_html()
        assert "PASSED" in html
        assert "#16a34a" in html  # green colour

    def test_contains_failed_label_red(
        self, failing_reporter: CertificationReporter
    ) -> None:
        html = failing_reporter.as_html()
        assert "FAILED" in html
        assert "#dc2626" in html  # red colour

    def test_no_failed_findings_shows_placeholder(
        self, passing_reporter: CertificationReporter
    ) -> None:
        html = passing_reporter.as_html()
        assert "No failed findings" in html

    def test_failed_findings_table_rows(
        self, failing_reporter: CertificationReporter
    ) -> None:
        html = failing_reporter.as_html()
        assert "<tr>" in html
        assert "phi.leakage" in html or "PHI exposed" in html

    def test_html_escaping_in_agent_name(self) -> None:
        result = _make_result()
        reporter = CertificationReporter(result, agent_name='Agent <"XSS">')
        html = reporter.as_html()
        assert '<"XSS">' not in html
        assert "&lt;" in html or "&quot;" in html

    def test_severity_colors_in_html(self, failing_reporter: CertificationReporter) -> None:
        html = failing_reporter.as_html()
        assert "#dc2626" in html

    def test_report_version_default(self, passing_reporter: CertificationReporter) -> None:
        parsed = json.loads(passing_reporter.as_json())
        assert parsed["report_version"] == "1.0"

    def test_custom_report_version(self) -> None:
        result = _make_result()
        reporter = CertificationReporter(result, report_version="2.5")
        parsed = json.loads(reporter.as_json())
        assert parsed["report_version"] == "2.5"

    def test_html_contains_domain(self, passing_reporter: CertificationReporter) -> None:
        html = passing_reporter.as_html()
        assert "healthcare" in html

    def test_html_contains_score_value(self, passing_reporter: CertificationReporter) -> None:
        html = passing_reporter.as_html()
        assert "85" in html

    def test_default_agent_name(self) -> None:
        result = _make_result()
        reporter = CertificationReporter(result)
        html = reporter.as_html()
        assert "Agent Under Evaluation" in html
