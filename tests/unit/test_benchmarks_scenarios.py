"""Unit tests for benchmarks.scenarios module."""
from __future__ import annotations

import pytest

from agent_vertical.benchmarks.scenarios import BenchmarkScenario, ScenarioLibrary
from agent_vertical.certification.risk_tier import RiskTier


# ---------------------------------------------------------------------------
# BenchmarkScenario (dataclass)
# ---------------------------------------------------------------------------


class TestBenchmarkScenario:
    def test_fields_accessible(self) -> None:
        scenario = BenchmarkScenario(
            scenario_id="hc-001",
            domain="healthcare",
            name="Test",
            description="A test scenario",
            user_input="What should I do?",
            expected_behaviours=("provide disclaimer",),
            prohibited_behaviours=("diagnose",),
            risk_tier=RiskTier.INFORMATIONAL,
            difficulty="easy",
            tags=("safety",),
        )
        assert scenario.scenario_id == "hc-001"
        assert scenario.domain == "healthcare"
        assert scenario.risk_tier == RiskTier.INFORMATIONAL
        assert scenario.difficulty == "easy"
        assert "safety" in scenario.tags

    def test_frozen_prevents_mutation(self) -> None:
        scenario = BenchmarkScenario(
            scenario_id="hc-001",
            domain="healthcare",
            name="Test",
            description="Desc",
            user_input="Input",
            expected_behaviours=(),
            prohibited_behaviours=(),
            risk_tier=RiskTier.INFORMATIONAL,
            difficulty="easy",
        )
        with pytest.raises((AttributeError, TypeError)):
            scenario.domain = "changed"  # type: ignore[misc]

    def test_expected_behaviours_is_tuple(self) -> None:
        scenario = BenchmarkScenario(
            scenario_id="x",
            domain="finance",
            name="X",
            description="D",
            user_input="U",
            expected_behaviours=("a", "b"),
            prohibited_behaviours=(),
            risk_tier=RiskTier.ADVISORY,
            difficulty="medium",
        )
        assert isinstance(scenario.expected_behaviours, tuple)

    def test_default_tags_empty(self) -> None:
        scenario = BenchmarkScenario(
            scenario_id="x",
            domain="legal",
            name="X",
            description="D",
            user_input="U",
            expected_behaviours=(),
            prohibited_behaviours=(),
            risk_tier=RiskTier.ADVISORY,
            difficulty="easy",
        )
        assert scenario.tags == ()


# ---------------------------------------------------------------------------
# ScenarioLibrary — initialisation and all_scenarios
# ---------------------------------------------------------------------------


class TestScenarioLibraryInit:
    def test_library_creates_40_scenarios(self) -> None:
        library = ScenarioLibrary()
        assert len(library.all_scenarios()) == 40

    def test_all_scenarios_sorted_by_id(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.all_scenarios()
        ids = [s.scenario_id for s in scenarios]
        assert ids == sorted(ids)

    def test_all_scenarios_returns_list(self) -> None:
        library = ScenarioLibrary()
        assert isinstance(library.all_scenarios(), list)


# ---------------------------------------------------------------------------
# ScenarioLibrary.get
# ---------------------------------------------------------------------------


class TestScenarioLibraryGet:
    def test_get_returns_scenario_by_id(self) -> None:
        library = ScenarioLibrary()
        all_scenarios = library.all_scenarios()
        first_id = all_scenarios[0].scenario_id
        result = library.get(first_id)
        assert result is not None
        assert result.scenario_id == first_id

    def test_get_nonexistent_returns_none(self) -> None:
        library = ScenarioLibrary()
        assert library.get("nonexistent-999") is None

    def test_get_all_ids_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        for scenario in library.all_scenarios():
            result = library.get(scenario.scenario_id)
            assert result is not None
            assert result.scenario_id == scenario.scenario_id


# ---------------------------------------------------------------------------
# ScenarioLibrary.for_domain
# ---------------------------------------------------------------------------


class TestScenarioLibraryForDomain:
    def test_for_domain_healthcare_returns_10(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("healthcare")
        assert len(scenarios) == 10

    def test_for_domain_finance_returns_10(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("finance")
        assert len(scenarios) == 10

    def test_for_domain_legal_returns_10(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("legal")
        assert len(scenarios) == 10

    def test_for_domain_education_returns_10(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("education")
        assert len(scenarios) == 10

    def test_for_domain_all_match_domain(self) -> None:
        library = ScenarioLibrary()
        for domain in ("healthcare", "finance", "legal", "education"):
            for scenario in library.for_domain(domain):
                assert scenario.domain == domain

    def test_for_domain_sorted_by_id(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.for_domain("healthcare")
        ids = [s.scenario_id for s in scenarios]
        assert ids == sorted(ids)

    def test_for_domain_unknown_returns_empty(self) -> None:
        library = ScenarioLibrary()
        assert library.for_domain("unknown_domain_xyz") == []


# ---------------------------------------------------------------------------
# ScenarioLibrary.by_difficulty
# ---------------------------------------------------------------------------


class TestScenarioLibraryByDifficulty:
    def test_by_difficulty_easy_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        easy = library.by_difficulty("easy")
        assert len(easy) > 0
        for scenario in easy:
            assert scenario.difficulty == "easy"

    def test_by_difficulty_medium_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        medium = library.by_difficulty("medium")
        assert len(medium) > 0
        for scenario in medium:
            assert scenario.difficulty == "medium"

    def test_by_difficulty_hard_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        hard = library.by_difficulty("hard")
        assert len(hard) > 0
        for scenario in hard:
            assert scenario.difficulty == "hard"

    def test_by_difficulty_unknown_returns_empty(self) -> None:
        library = ScenarioLibrary()
        assert library.by_difficulty("impossible") == []

    def test_by_difficulty_sorted_by_id(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_difficulty("easy")
        ids = [s.scenario_id for s in scenarios]
        assert ids == sorted(ids)

    def test_easy_medium_hard_totals_40(self) -> None:
        library = ScenarioLibrary()
        total = (
            len(library.by_difficulty("easy"))
            + len(library.by_difficulty("medium"))
            + len(library.by_difficulty("hard"))
        )
        assert total == 40


# ---------------------------------------------------------------------------
# ScenarioLibrary.by_risk_tier
# ---------------------------------------------------------------------------


class TestScenarioLibraryByRiskTier:
    def test_by_risk_tier_informational_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_risk_tier(RiskTier.INFORMATIONAL)
        assert len(scenarios) > 0
        for scenario in scenarios:
            assert scenario.risk_tier == RiskTier.INFORMATIONAL

    def test_by_risk_tier_advisory_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_risk_tier(RiskTier.ADVISORY)
        assert len(scenarios) > 0
        for scenario in scenarios:
            assert scenario.risk_tier == RiskTier.ADVISORY

    def test_by_risk_tier_decision_support_returns_scenarios(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_risk_tier(RiskTier.DECISION_SUPPORT)
        assert len(scenarios) > 0
        for scenario in scenarios:
            assert scenario.risk_tier == RiskTier.DECISION_SUPPORT

    def test_all_tiers_together_equal_40(self) -> None:
        library = ScenarioLibrary()
        total = (
            len(library.by_risk_tier(RiskTier.INFORMATIONAL))
            + len(library.by_risk_tier(RiskTier.ADVISORY))
            + len(library.by_risk_tier(RiskTier.DECISION_SUPPORT))
        )
        assert total == 40

    def test_by_risk_tier_sorted_by_id(self) -> None:
        library = ScenarioLibrary()
        scenarios = library.by_risk_tier(RiskTier.ADVISORY)
        ids = [s.scenario_id for s in scenarios]
        assert ids == sorted(ids)
