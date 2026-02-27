"""Tests for agent_vertical.gap_tracker.scanner."""
from __future__ import annotations

from typing import Any

import pytest

from agent_vertical.gap_tracker.scanner import (
    GapReport,
    GapSeverity,
    TemplateGap,
    TemplateGapScanner,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def scanner() -> TemplateGapScanner:
    return TemplateGapScanner()


@pytest.fixture()
def full_config() -> dict[str, Any]:
    return {
        "domain": "healthcare",
        "risk_tier": "advisory",
        "version": "1.0.0",
        "disclaimer": (
            "This output does not constitute medical advice and is for "
            "informational purposes only. Always consult a licensed professional."
        ),
        "input_validation": {"enabled": True},
        "rate_limiting": {"rpm": 60},
        "sources": ["medline", "pubmed"],
        "audit_trail": {"enabled": True},
        "description": (
            "A comprehensive healthcare information assistant for general "
            "medical information lookup and triage support."
        ),
    }


# ---------------------------------------------------------------------------
# TemplateGap
# ---------------------------------------------------------------------------


class TestTemplateGap:
    def test_is_frozen(self) -> None:
        gap = TemplateGap(
            gap_id="test.gap",
            title="Test",
            description="A test gap",
            severity=GapSeverity.LOW,
            remediation="Fix it.",
        )
        with pytest.raises((AttributeError, TypeError)):
            gap.gap_id = "other"  # type: ignore[misc]

    def test_optional_field_path_defaults_empty(self) -> None:
        gap = TemplateGap(
            gap_id="test.gap",
            title="Test",
            description="Desc",
            severity=GapSeverity.INFO,
            remediation="Do something.",
        )
        assert gap.field_path == ""


# ---------------------------------------------------------------------------
# GapReport
# ---------------------------------------------------------------------------


class TestGapReport:
    def _make_report(self, gaps: list[TemplateGap]) -> GapReport:
        import datetime
        return GapReport(
            template_identifier="test_template",
            gaps=tuple(gaps),
            completion_score=80.0,
            scanned_at=datetime.datetime.now(datetime.timezone.utc),
            total_rules_run=5,
        )

    def test_critical_gaps_filter(self) -> None:
        gaps = [
            TemplateGap("g1", "Critical", "Desc", GapSeverity.CRITICAL, "Fix"),
            TemplateGap("g2", "High", "Desc", GapSeverity.HIGH, "Fix"),
        ]
        report = self._make_report(gaps)
        assert len(report.critical_gaps) == 1
        assert report.critical_gaps[0].gap_id == "g1"

    def test_high_gaps_filter(self) -> None:
        gaps = [
            TemplateGap("g1", "Critical", "Desc", GapSeverity.CRITICAL, "Fix"),
            TemplateGap("g2", "High", "Desc", GapSeverity.HIGH, "Fix"),
        ]
        report = self._make_report(gaps)
        assert len(report.high_gaps) == 1

    def test_is_deployment_ready_no_critical(self) -> None:
        gaps = [TemplateGap("g1", "High", "Desc", GapSeverity.HIGH, "Fix")]
        report = self._make_report(gaps)
        assert report.is_deployment_ready is True

    def test_is_not_deployment_ready_with_critical(self) -> None:
        gaps = [TemplateGap("g1", "Critical", "Desc", GapSeverity.CRITICAL, "Fix")]
        report = self._make_report(gaps)
        assert report.is_deployment_ready is False

    def test_gap_count(self) -> None:
        gaps = [
            TemplateGap("g1", "A", "Desc", GapSeverity.HIGH, "Fix"),
            TemplateGap("g2", "B", "Desc", GapSeverity.LOW, "Fix"),
        ]
        report = self._make_report(gaps)
        assert report.gap_count == 2

    def test_gaps_by_severity(self) -> None:
        gaps = [
            TemplateGap("g1", "Critical", "Desc", GapSeverity.CRITICAL, "Fix"),
            TemplateGap("g2", "Low", "Desc", GapSeverity.LOW, "Fix"),
        ]
        report = self._make_report(gaps)
        grouped = report.gaps_by_severity()
        assert len(grouped["critical"]) == 1
        assert len(grouped["low"]) == 1
        assert len(grouped["high"]) == 0


# ---------------------------------------------------------------------------
# TemplateGapScanner
# ---------------------------------------------------------------------------


class TestTemplatGapScannerFullConfig:
    def test_no_gaps_for_full_config(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        report = scanner.scan(full_config, "full_template")
        assert report.gap_count == 0

    def test_completion_score_100_for_full_config(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        report = scanner.scan(full_config, "full_template")
        assert report.completion_score == pytest.approx(100.0)

    def test_is_deployment_ready_for_full_config(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        assert scanner.scan(full_config).is_deployment_ready is True


class TestTemplateGapScannerMissingFields:
    def test_missing_disclaimer_is_critical(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        config = {k: v for k, v in full_config.items() if k != "disclaimer"}
        report = scanner.scan(config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "missing.disclaimer" in gap_ids
        critical_ids = [g.gap_id for g in report.critical_gaps]
        assert "missing.disclaimer" in critical_ids

    def test_missing_domain_detected(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        config = {k: v for k, v in full_config.items() if k != "domain"}
        report = scanner.scan(config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "missing.domain" in gap_ids

    def test_invalid_risk_tier_detected(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        config = dict(full_config)
        config["risk_tier"] = "critical"  # invalid
        report = scanner.scan(config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "missing.risk_tier" in gap_ids

    def test_decision_support_missing_human_gate(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        config = dict(full_config)
        config["risk_tier"] = "decision_support"
        # No human_review_gate key
        report = scanner.scan(config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "governance.missing_human_review_gate" in gap_ids

    def test_decision_support_with_human_gate_no_gap(
        self, scanner: TemplateGapScanner, full_config: dict[str, Any]
    ) -> None:
        config = dict(full_config)
        config["risk_tier"] = "decision_support"
        config["human_review_gate"] = {"enabled": True}
        report = scanner.scan(config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "governance.missing_human_review_gate" not in gap_ids

    def test_empty_config_has_many_gaps(self, scanner: TemplateGapScanner) -> None:
        report = scanner.scan({})
        assert report.gap_count > 0
        assert report.is_deployment_ready is False

    def test_gaps_sorted_critical_first(
        self, scanner: TemplateGapScanner
    ) -> None:
        report = scanner.scan({})
        if report.gap_count >= 2:
            first_order = _severity_order(report.gaps[0].severity)
            second_order = _severity_order(report.gaps[1].severity)
            assert first_order <= second_order


def _severity_order(sev: GapSeverity) -> int:
    order = {
        GapSeverity.CRITICAL: 0,
        GapSeverity.HIGH: 1,
        GapSeverity.MEDIUM: 2,
        GapSeverity.LOW: 3,
        GapSeverity.INFO: 4,
    }
    return order[sev]


class TestTemplateGapScannerCustomRules:
    def test_register_custom_rule(self, scanner: TemplateGapScanner) -> None:
        initial_count = scanner.rule_count()

        def custom_rule(config: dict[str, Any]) -> TemplateGap | None:
            if not config.get("custom_field"):
                return TemplateGap(
                    gap_id="custom.missing_field",
                    title="Missing Custom Field",
                    description="Custom field is required.",
                    severity=GapSeverity.MEDIUM,
                    remediation="Add 'custom_field' to config.",
                )
            return None

        scanner.register_rule(custom_rule)
        assert scanner.rule_count() == initial_count + 1

    def test_custom_rule_triggers(self, full_config: dict[str, Any]) -> None:
        def custom_rule(config: dict[str, Any]) -> TemplateGap | None:
            if not config.get("my_field"):
                return TemplateGap(
                    gap_id="custom.my_field",
                    title="My Field Missing",
                    description="My field is needed.",
                    severity=GapSeverity.INFO,
                    remediation="Add 'my_field'.",
                )
            return None

        scanner = TemplateGapScanner(extra_rules=[custom_rule])
        report = scanner.scan(full_config)
        gap_ids = [g.gap_id for g in report.gaps]
        assert "custom.my_field" in gap_ids

    def test_no_defaults_only_custom(self, full_config: dict[str, Any]) -> None:
        def custom_rule(config: dict[str, Any]) -> TemplateGap | None:
            return TemplateGap(
                gap_id="always.fires",
                title="Always",
                description="Always fires.",
                severity=GapSeverity.INFO,
                remediation="None.",
            )

        scanner = TemplateGapScanner(extra_rules=[custom_rule], include_defaults=False)
        report = scanner.scan(full_config)
        assert report.gap_count == 1
        assert report.gaps[0].gap_id == "always.fires"


class TestScanMetadata:
    def test_template_identifier_in_report(self, scanner: TemplateGapScanner) -> None:
        report = scanner.scan({}, template_identifier="my_template")
        assert report.template_identifier == "my_template"

    def test_total_rules_run_matches(self, scanner: TemplateGapScanner) -> None:
        report = scanner.scan({})
        assert report.total_rules_run == scanner.rule_count()

    def test_scanned_at_is_utc(self, scanner: TemplateGapScanner) -> None:
        import datetime
        report = scanner.scan({})
        assert report.scanned_at.tzinfo is not None

    def test_completion_score_between_0_and_100(
        self, scanner: TemplateGapScanner
    ) -> None:
        report = scanner.scan({})
        assert 0.0 <= report.completion_score <= 100.0
