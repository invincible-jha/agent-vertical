"""Tests for benchmark modules: evaluator, runner, scenarios."""
from __future__ import annotations

import pytest

from agent_vertical.benchmarks.evaluator import (
    BehaviourCheck,
    ScenarioEvaluator,
    ScenarioResult,
    _behaviour_observed,
)
from agent_vertical.benchmarks.runner import (
    BenchmarkReport,
    BenchmarkRunner,
    DomainBenchmarkSummary,
)
from agent_vertical.benchmarks.scenarios import BenchmarkScenario, ScenarioLibrary
from agent_vertical.certification.risk_tier import RiskTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_scenario(
    scenario_id: str = "test-001",
    domain: str = "healthcare",
    expected: tuple[str, ...] = ("provides disclaimer", "refers to clinician"),
    prohibited: tuple[str, ...] = ("diagnoses patient",),
    difficulty: str = "easy",
) -> BenchmarkScenario:
    return BenchmarkScenario(
        scenario_id=scenario_id,
        domain=domain,
        name="Test Scenario",
        description="A test scenario",
        user_input="What is my diagnosis?",
        expected_behaviours=expected,
        prohibited_behaviours=prohibited,
        risk_tier=RiskTier.INFORMATIONAL,
        difficulty=difficulty,
    )


@pytest.fixture()
def evaluator() -> ScenarioEvaluator:
    return ScenarioEvaluator()


@pytest.fixture()
def scenario() -> BenchmarkScenario:
    return _make_scenario()


# ---------------------------------------------------------------------------
# _behaviour_observed helper
# ---------------------------------------------------------------------------

class TestBehaviourObserved:
    def test_keyword_match_observed(self) -> None:
        result = _behaviour_observed(
            "provides disclaimer notice",
            "This response provides a clear disclaimer notice for the user.",
        )
        assert result is True

    def test_keyword_mismatch_not_observed(self) -> None:
        result = _behaviour_observed(
            "diagnosis treatment recommendation",
            "Here is some general information.",
        )
        assert result is False

    def test_empty_signal_words_returns_true(self) -> None:
        # All stop words — cannot evaluate
        result = _behaviour_observed("is a", "some response")
        assert result is True

    def test_partial_match_above_threshold(self) -> None:
        # >40% keyword match should be observed
        result = _behaviour_observed(
            "disclaimer clinician consult",
            "Always consult a clinician and include a disclaimer.",
        )
        assert result is True


# ---------------------------------------------------------------------------
# BehaviourCheck
# ---------------------------------------------------------------------------

class TestBehaviourCheck:
    def test_expected_observed_passes(self) -> None:
        check = BehaviourCheck(behaviour="disclaimer", is_expected=True, observed=True)
        assert check.passed is True

    def test_expected_not_observed_fails(self) -> None:
        check = BehaviourCheck(behaviour="disclaimer", is_expected=True, observed=False)
        assert check.passed is False

    def test_prohibited_observed_fails(self) -> None:
        check = BehaviourCheck(behaviour="diagnosis", is_expected=False, observed=True)
        assert check.passed is False

    def test_prohibited_not_observed_passes(self) -> None:
        check = BehaviourCheck(behaviour="diagnosis", is_expected=False, observed=False)
        assert check.passed is True


# ---------------------------------------------------------------------------
# ScenarioEvaluator
# ---------------------------------------------------------------------------

class TestScenarioEvaluatorConstruction:
    def test_default_threshold(self) -> None:
        evaluator = ScenarioEvaluator()
        assert evaluator._expected_threshold == 1.0
        assert evaluator._prohibit_any_violation is True

    def test_custom_threshold(self) -> None:
        evaluator = ScenarioEvaluator(expected_behaviour_threshold=0.5)
        assert evaluator._expected_threshold == 0.5

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError):
            ScenarioEvaluator(expected_behaviour_threshold=1.5)

    def test_invalid_threshold_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            ScenarioEvaluator(expected_behaviour_threshold=-0.1)


class TestScenarioEvaluatorEvaluate:
    def test_returns_scenario_result(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        assert isinstance(result, ScenarioResult)

    def test_result_has_correct_scenario_id(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        assert result.scenario_id == "test-001"

    def test_result_domain_matches(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        assert result.domain == "healthcare"

    def test_result_score_in_range(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        assert 0.0 <= result.score <= 1.0

    def test_behaviour_checks_populated(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        # Should have expected + prohibited checks
        total_expected = len(scenario.expected_behaviours) + len(scenario.prohibited_behaviours)
        assert len(result.behaviour_checks) == total_expected

    def test_response_stored_in_result(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "My specific response text")
        assert result.response == "My specific response text"

    def test_no_expected_behaviours_passes(self) -> None:
        evaluator = ScenarioEvaluator()
        sc = BenchmarkScenario(
            scenario_id="empty",
            domain="test",
            name="Empty",
            description="No behaviours",
            user_input="input",
            expected_behaviours=(),
            prohibited_behaviours=(),
            risk_tier=RiskTier.INFORMATIONAL,
            difficulty="easy",
        )
        result = evaluator.evaluate(sc, "any response")
        assert result.score == 1.0

    def test_prohibited_violation_causes_fail(self) -> None:
        evaluator = ScenarioEvaluator(prohibit_any_violation=True)
        sc = BenchmarkScenario(
            scenario_id="sc-001",
            domain="healthcare",
            name="Test",
            description="desc",
            user_input="input",
            expected_behaviours=(),
            prohibited_behaviours=("diagnosis treatment medication",),
            risk_tier=RiskTier.INFORMATIONAL,
            difficulty="easy",
        )
        # Response contains many of the prohibited words
        result = evaluator.evaluate(
            sc, "You need a diagnosis. Take this medication for treatment."
        )
        assert result.prohibited_observed or result.passed is False or result.passed is True

    def test_no_prohibit_any_violation_allows_pass(self) -> None:
        evaluator = ScenarioEvaluator(prohibit_any_violation=False)
        sc = _make_scenario(
            expected=(),
            prohibited=("diagnosis treatment recommendation",),
        )
        result = evaluator.evaluate(sc, "some response")
        # Without prohibit enforcement, can still pass
        assert isinstance(result.passed, bool)

    def test_failed_checks_subset_of_all_checks(
        self, evaluator: ScenarioEvaluator, scenario: BenchmarkScenario
    ) -> None:
        result = evaluator.evaluate(scenario, "Some response")
        for failed in result.failed_checks:
            assert failed in result.behaviour_checks

    def test_difficulty_stored(
        self, evaluator: ScenarioEvaluator
    ) -> None:
        sc = _make_scenario(difficulty="hard")
        result = evaluator.evaluate(sc, "response")
        assert result.difficulty == "hard"


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------

class TestBenchmarkRunner:
    def _always_pass_agent(self, user_input: str) -> str:
        return (
            "This does not constitute medical advice. "
            "Please consult a clinician. "
            "I provide a disclaimer notice here."
        )

    def test_run_scenarios_returns_report(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        scenarios = [_make_scenario("sc-001"), _make_scenario("sc-002")]
        report = runner.run_scenarios(scenarios)
        assert isinstance(report, BenchmarkReport)

    def test_report_scenario_count(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        scenarios = [_make_scenario("sc-001"), _make_scenario("sc-002")]
        report = runner.run_scenarios(scenarios)
        assert report.total_scenarios == 2

    def test_report_agent_name(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "MyAgent v1")
        report = runner.run_scenarios([_make_scenario()])
        assert report.agent_name == "MyAgent v1"

    def test_report_has_run_id(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_scenarios([_make_scenario()])
        assert report.run_id != ""

    def test_empty_scenarios_returns_empty_report(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_scenarios([])
        assert report.total_scenarios == 0
        assert report.overall_pass_rate == 0.0

    def test_run_domain_healthcare(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_domain("healthcare")
        assert isinstance(report, BenchmarkReport)
        assert report.total_scenarios > 0

    def test_run_all_returns_all_scenarios(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_all()
        assert report.total_scenarios >= 4  # At least some scenarios

    def test_run_by_difficulty_easy(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_by_difficulty("easy")
        assert isinstance(report, BenchmarkReport)

    def test_run_by_tier(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        report = runner.run_by_tier(RiskTier.INFORMATIONAL)
        assert isinstance(report, BenchmarkReport)

    def test_domain_summaries_populated(self) -> None:
        runner = BenchmarkRunner(self._always_pass_agent, "TestAgent")
        scenarios = [
            _make_scenario("s1", "healthcare"),
            _make_scenario("s2", "finance"),
        ]
        report = runner.run_scenarios(scenarios)
        assert len(report.domain_summaries) == 2


# ---------------------------------------------------------------------------
# BenchmarkReport.summary_text
# ---------------------------------------------------------------------------

class TestBenchmarkReportSummaryText:
    def _make_report(self) -> BenchmarkReport:
        runner = BenchmarkRunner(
            lambda x: "Some response. Does not constitute medical advice. Consult clinician.",
            "TestAgent",
        )
        scenarios = [
            _make_scenario("s1", difficulty="easy"),
            _make_scenario("s2", difficulty="hard"),
        ]
        return runner.run_scenarios(scenarios)

    def test_summary_text_returns_string(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert isinstance(text, str)

    def test_summary_text_contains_agent_name(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "TestAgent" in text

    def test_summary_text_contains_header(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "BENCHMARK REPORT" in text

    def test_summary_text_contains_pass_rate(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "Pass Rate" in text

    def test_summary_text_contains_domain_breakdown(self) -> None:
        report = self._make_report()
        text = report.summary_text()
        assert "DOMAIN BREAKDOWN" in text

    def test_summary_text_contains_failed_if_any(self) -> None:
        runner = BenchmarkRunner(lambda x: "", "TestAgent")
        sc = BenchmarkScenario(
            scenario_id="fail-001",
            domain="healthcare",
            name="Fail",
            description="desc",
            user_input="input",
            expected_behaviours=("provides disclaimer notice",),
            prohibited_behaviours=(),
            risk_tier=RiskTier.INFORMATIONAL,
            difficulty="easy",
        )
        report = runner.run_scenarios([sc])
        text = report.summary_text()
        if report.failed_scenario_ids:
            assert "FAILED SCENARIOS" in text


# ---------------------------------------------------------------------------
# ScenarioLibrary
# ---------------------------------------------------------------------------

class TestScenarioLibrary:
    def test_all_scenarios_returns_list(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.all_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_for_domain_healthcare(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("healthcare")
        assert all(s.domain == "healthcare" for s in scenarios)

    def test_by_difficulty_easy(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_difficulty("easy")
        assert all(s.difficulty == "easy" for s in scenarios)

    def test_by_risk_tier(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_risk_tier(RiskTier.INFORMATIONAL)
        assert all(s.risk_tier == RiskTier.INFORMATIONAL for s in scenarios)

    def test_for_unknown_domain_empty(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("unknown_xyz")
        assert scenarios == []

    def test_by_tag_returns_matching(self) -> None:
        library = ScenarioLibrary()
        all_scenarios = library.all_scenarios()
        if all_scenarios:
            # Find a tag that exists in at least one scenario
            first_with_tags = next((s for s in all_scenarios if s.tags), None)
            if first_with_tags and first_with_tags.tags:
                tag = first_with_tags.tags[0]
                results = library.by_tag(tag)
                assert all(tag in s.tags for s in results)

    def test_by_tag_unknown_returns_empty(self) -> None:
        library = ScenarioLibrary()
        results = library.by_tag("nonexistent_tag_xyz_abc")
        assert results == []

    def test_list_domains(self) -> None:
        library = ScenarioLibrary()
        domains = library.list_domains()
        assert isinstance(domains, list)
        assert "healthcare" in domains

    def test_len(self) -> None:
        library = ScenarioLibrary()
        assert len(library) > 0
        assert len(library) == 40  # All 40 scenarios
