"""Unit tests for benchmarks.runner module."""
from __future__ import annotations

import pytest

from agent_vertical.benchmarks.evaluator import ScenarioEvaluator
from agent_vertical.benchmarks.runner import (
    BenchmarkReport,
    BenchmarkRunner,
    DomainBenchmarkSummary,
)
from agent_vertical.benchmarks.scenarios import BenchmarkScenario, ScenarioLibrary
from agent_vertical.certification.risk_tier import RiskTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _always_pass_agent(user_input: str) -> str:
    """Agent stub that returns a response designed to pass most heuristic checks."""
    return (
        "I cannot provide a diagnosis. This is for informational purposes only. "
        "Please consult a licensed clinician or attorney for advice. "
        "Disclaimer: this output does not constitute medical, legal, or financial advice."
    )


def _always_fail_agent(user_input: str) -> str:
    """Agent stub that returns a minimal response unlikely to trigger expected keywords."""
    return "xyz"


def _make_scenario(
    scenario_id: str = "test-001",
    domain: str = "healthcare",
    difficulty: str = "easy",
    expected: tuple[str, ...] = ("disclaimer information",),
    prohibited: tuple[str, ...] = (),
    user_input: str = "test input",
) -> BenchmarkScenario:
    return BenchmarkScenario(
        scenario_id=scenario_id,
        domain=domain,
        name="Test",
        description="Test scenario",
        user_input=user_input,
        expected_behaviours=expected,
        prohibited_behaviours=prohibited,
        risk_tier=RiskTier.INFORMATIONAL,
        difficulty=difficulty,
        tags=(),
    )


# ---------------------------------------------------------------------------
# DomainBenchmarkSummary (dataclass)
# ---------------------------------------------------------------------------


class TestDomainBenchmarkSummary:
    def test_fields_stored(self) -> None:
        summary = DomainBenchmarkSummary(
            domain="healthcare",
            total_scenarios=10,
            passed_scenarios=8,
            failed_scenarios=2,
            pass_rate=0.8,
            average_score=0.85,
            by_difficulty={"easy": 1.0, "hard": 0.5},
        )
        assert summary.domain == "healthcare"
        assert summary.total_scenarios == 10
        assert summary.pass_rate == 0.8
        assert summary.by_difficulty["easy"] == 1.0

    def test_default_by_difficulty_is_empty(self) -> None:
        summary = DomainBenchmarkSummary(
            domain="finance",
            total_scenarios=5,
            passed_scenarios=3,
            failed_scenarios=2,
            pass_rate=0.6,
            average_score=0.7,
        )
        assert summary.by_difficulty == {}


# ---------------------------------------------------------------------------
# BenchmarkReport — summary_text
# ---------------------------------------------------------------------------


class TestBenchmarkReportSummaryText:
    def _make_report(self) -> BenchmarkReport:
        return BenchmarkReport(
            run_id="2024-01-01T00:00:00+00:00",
            agent_name="TestAgent",
            total_scenarios=10,
            passed_scenarios=8,
            failed_scenarios=2,
            overall_pass_rate=0.8,
            overall_average_score=0.87,
            domain_summaries=[
                DomainBenchmarkSummary(
                    domain="healthcare",
                    total_scenarios=5,
                    passed_scenarios=4,
                    failed_scenarios=1,
                    pass_rate=0.8,
                    average_score=0.85,
                    by_difficulty={"easy": 1.0},
                ),
                DomainBenchmarkSummary(
                    domain="finance",
                    total_scenarios=5,
                    passed_scenarios=4,
                    failed_scenarios=1,
                    pass_rate=0.8,
                    average_score=0.89,
                ),
            ],
            scenario_results=[],
            failed_scenario_ids=["hc-005", "fin-003"],
        )

    def test_summary_text_contains_agent_name(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "TestAgent" in text

    def test_summary_text_contains_run_id(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "2024-01-01" in text

    def test_summary_text_contains_pass_rate(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "80.0%" in text

    def test_summary_text_contains_domain_names(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "healthcare" in text
        assert "finance" in text

    def test_summary_text_contains_failed_scenario_ids(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "hc-005" in text
        assert "fin-003" in text

    def test_summary_text_no_failed_ids_omits_failed_section(self) -> None:
        report = BenchmarkReport(
            run_id="2024-01-01",
            agent_name="TestAgent",
            total_scenarios=5,
            passed_scenarios=5,
            failed_scenarios=0,
            overall_pass_rate=1.0,
            overall_average_score=1.0,
            failed_scenario_ids=[],
        )
        text = report.summary_text()
        assert "FAILED SCENARIOS" not in text

    def test_summary_text_domains_sorted(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        finance_pos = text.index("finance")
        healthcare_pos = text.index("healthcare")
        assert finance_pos < healthcare_pos

    def test_summary_text_contains_total_scenarios(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "10" in text

    def test_summary_text_is_string(self) -> None:
        report = self._make_report()
        assert isinstance(report.summary_text(), str)


# ---------------------------------------------------------------------------
# BenchmarkRunner — initialisation
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerInit:
    def test_default_agent_name(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        assert runner is not None

    def test_custom_agent_name(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent, agent_name="MyAgent")
        assert runner is not None

    def test_custom_evaluator_accepted(self) -> None:
        evaluator = ScenarioEvaluator(expected_behaviour_threshold=0.5)
        runner = BenchmarkRunner(_always_pass_agent, evaluator=evaluator)
        assert runner is not None


# ---------------------------------------------------------------------------
# BenchmarkRunner.run_scenarios
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerRunScenarios:
    def test_run_empty_list_returns_empty_report(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_scenarios([])
        assert report.total_scenarios == 0
        assert report.passed_scenarios == 0
        assert report.failed_scenarios == 0

    def test_run_empty_list_pass_rate_is_zero(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_scenarios([])
        assert report.overall_pass_rate == 0.0

    def test_run_single_scenario_returns_one_result(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        scenario = _make_scenario(expected=(), prohibited=())
        report = runner.run_scenarios([scenario])
        assert report.total_scenarios == 1
        assert len(report.scenario_results) == 1

    def test_run_scenarios_agent_callable_is_called(self) -> None:
        call_log: list[str] = []

        def tracking_agent(user_input: str) -> str:
            call_log.append(user_input)
            return "disclaimer information"

        runner = BenchmarkRunner(tracking_agent)
        scenarios = [
            _make_scenario(scenario_id="s1", user_input="q1"),
            _make_scenario(scenario_id="s2", user_input="q2"),
        ]
        runner.run_scenarios(scenarios)
        assert call_log == ["q1", "q2"]

    def test_report_agent_name_set(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent, agent_name="SpecialAgent")
        report = runner.run_scenarios([_make_scenario(expected=(), prohibited=())])
        assert report.agent_name == "SpecialAgent"

    def test_report_run_id_is_iso_timestamp(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_scenarios([])
        # ISO 8601 timestamps contain 'T' and '+'
        assert "T" in report.run_id

    def test_multiple_domains_create_domain_summaries(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        scenarios = [
            _make_scenario(scenario_id="hc-001", domain="healthcare", expected=(), prohibited=()),
            _make_scenario(scenario_id="fin-001", domain="finance", expected=(), prohibited=()),
            _make_scenario(scenario_id="edu-001", domain="education", expected=(), prohibited=()),
        ]
        report = runner.run_scenarios(scenarios)
        domains = {s.domain for s in report.domain_summaries}
        assert domains == {"healthcare", "finance", "education"}

    def test_failed_scenario_ids_populated(self) -> None:
        runner = BenchmarkRunner(_always_fail_agent)
        # Scenario with expected keyword that won't match "xyz"
        scenario = _make_scenario(
            scenario_id="hc-fail-01",
            expected=("zzz_unique_token_xyz",),
            prohibited=(),
        )
        report = runner.run_scenarios([scenario])
        assert "hc-fail-01" in report.failed_scenario_ids

    def test_by_difficulty_breakdown_computed(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        scenarios = [
            _make_scenario(scenario_id="s1", difficulty="easy", expected=(), prohibited=()),
            _make_scenario(scenario_id="s2", difficulty="hard", expected=(), prohibited=()),
        ]
        report = runner.run_scenarios(scenarios)
        # All in same domain "healthcare"
        assert len(report.domain_summaries) == 1
        by_diff = report.domain_summaries[0].by_difficulty
        assert "easy" in by_diff
        assert "hard" in by_diff


# ---------------------------------------------------------------------------
# BenchmarkRunner.run_domain
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerRunDomain:
    def test_run_domain_healthcare_returns_report(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_domain("healthcare")
        assert isinstance(report, BenchmarkReport)

    def test_run_domain_only_includes_correct_domain(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_domain("finance")
        for result in report.scenario_results:
            assert result.domain == "finance"

    def test_run_domain_healthcare_has_scenarios(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_domain("healthcare")
        assert report.total_scenarios > 0


# ---------------------------------------------------------------------------
# BenchmarkRunner.run_all
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerRunAll:
    def test_run_all_returns_all_40_scenarios(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_all()
        assert report.total_scenarios == 40

    def test_run_all_covers_all_four_domains(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_all()
        domains = {r.domain for r in report.scenario_results}
        assert "healthcare" in domains
        assert "finance" in domains
        assert "legal" in domains
        assert "education" in domains

    def test_run_all_summary_text_is_str(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_all()
        assert isinstance(report.summary_text(), str)


# ---------------------------------------------------------------------------
# BenchmarkRunner.run_by_difficulty
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerRunByDifficulty:
    def test_run_easy_only_includes_easy(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_difficulty("easy")
        for result in report.scenario_results:
            assert result.difficulty == "easy"

    def test_run_hard_only_includes_hard(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_difficulty("hard")
        for result in report.scenario_results:
            assert result.difficulty == "hard"

    def test_run_medium_returns_report(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_difficulty("medium")
        assert isinstance(report, BenchmarkReport)


# ---------------------------------------------------------------------------
# BenchmarkRunner.run_by_tier
# ---------------------------------------------------------------------------


class TestBenchmarkRunnerRunByTier:
    def test_run_informational_tier(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_tier(RiskTier.INFORMATIONAL)
        assert isinstance(report, BenchmarkReport)

    def test_run_advisory_tier(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_tier(RiskTier.ADVISORY)
        assert isinstance(report, BenchmarkReport)

    def test_run_decision_support_tier(self) -> None:
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_tier(RiskTier.DECISION_SUPPORT)
        assert isinstance(report, BenchmarkReport)

    def test_run_by_tier_only_includes_matching_tier(self) -> None:
        library = ScenarioLibrary()
        runner = BenchmarkRunner(_always_pass_agent)
        report = runner.run_by_tier(RiskTier.INFORMATIONAL)
        informational_scenarios = library.by_risk_tier(RiskTier.INFORMATIONAL)
        assert report.total_scenarios == len(informational_scenarios)
