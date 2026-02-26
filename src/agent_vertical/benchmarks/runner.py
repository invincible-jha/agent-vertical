"""Benchmark runner — orchestrate scenario evaluation and produce benchmark reports.

:class:`BenchmarkRunner` accepts a callable that produces agent responses,
runs it against a set of :class:`BenchmarkScenario` objects, and returns
a :class:`BenchmarkReport` with aggregated metrics.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent_vertical.benchmarks.evaluator import ScenarioEvaluator, ScenarioResult
from agent_vertical.benchmarks.scenarios import BenchmarkScenario, ScenarioLibrary
from agent_vertical.certification.risk_tier import RiskTier


@dataclass
class DomainBenchmarkSummary:
    """Aggregate benchmark metrics for a single domain.

    Attributes
    ----------
    domain:
        Domain identifier.
    total_scenarios:
        Number of scenarios evaluated.
    passed_scenarios:
        Number of scenarios that passed.
    failed_scenarios:
        Number of scenarios that failed.
    pass_rate:
        Fraction of scenarios that passed, in [0.0, 1.0].
    average_score:
        Mean :attr:`~agent_vertical.benchmarks.evaluator.ScenarioResult.score`
        across all scenarios.
    by_difficulty:
        Mapping of difficulty label to pass rate.
    """

    domain: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    pass_rate: float
    average_score: float
    by_difficulty: dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Full benchmark report across all evaluated scenarios.

    Attributes
    ----------
    run_id:
        Unique identifier for this benchmark run (UTC ISO 8601 timestamp).
    agent_name:
        Human-readable name of the agent under test.
    total_scenarios:
        Total number of scenarios evaluated.
    passed_scenarios:
        Total passed.
    failed_scenarios:
        Total failed.
    overall_pass_rate:
        Fraction of all scenarios that passed.
    overall_average_score:
        Mean score across all scenarios.
    domain_summaries:
        Per-domain metrics.
    scenario_results:
        All individual :class:`ScenarioResult` objects.
    failed_scenario_ids:
        IDs of scenarios that failed.
    """

    run_id: str
    agent_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    overall_pass_rate: float
    overall_average_score: float
    domain_summaries: list[DomainBenchmarkSummary] = field(default_factory=list)
    scenario_results: list[ScenarioResult] = field(default_factory=list)
    failed_scenario_ids: list[str] = field(default_factory=list)

    def summary_text(self) -> str:
        """Return a plain-text summary of the benchmark report.

        Returns
        -------
        str
        """
        lines: list[str] = [
            "=" * 72,
            "BENCHMARK REPORT",
            "=" * 72,
            f"Agent       : {self.agent_name}",
            f"Run ID      : {self.run_id}",
            f"Scenarios   : {self.total_scenarios}",
            f"Passed      : {self.passed_scenarios}",
            f"Failed      : {self.failed_scenarios}",
            f"Pass Rate   : {self.overall_pass_rate:.1%}",
            f"Avg. Score  : {self.overall_average_score:.3f}",
            "-" * 72,
            "DOMAIN BREAKDOWN",
        ]
        for summary in sorted(self.domain_summaries, key=lambda s: s.domain):
            lines.append(
                f"  {summary.domain:<16} "
                f"pass={summary.pass_rate:.1%}  "
                f"avg={summary.average_score:.3f}  "
                f"({summary.passed_scenarios}/{summary.total_scenarios})"
            )
        if self.failed_scenario_ids:
            lines.append("-" * 72)
            lines.append("FAILED SCENARIOS")
            for sid in sorted(self.failed_scenario_ids):
                lines.append(f"  {sid}")
        lines.append("=" * 72)
        return "\n".join(lines)


# Type alias for the agent response callable
AgentResponseCallable = Callable[[str], str]


class BenchmarkRunner:
    """Run benchmark scenarios against an agent response callable.

    :class:`BenchmarkRunner` orchestrates scenario selection, response
    generation, evaluation, and report generation.

    Parameters
    ----------
    agent_callable:
        A callable that accepts a user input string and returns the agent's
        response string.  This abstracts the agent implementation so the
        runner works with any agent interface.
    agent_name:
        Human-readable name of the agent under test.
    evaluator:
        Optional custom :class:`ScenarioEvaluator`.  Defaults to the
        standard evaluator.

    Example
    -------
    ::

        def my_agent(user_input: str) -> str:
            # Your agent implementation here
            return "I cannot diagnose conditions. Please consult a clinician."

        runner = BenchmarkRunner(my_agent, agent_name="ClinicalDocAgent v1")
        report = runner.run_domain("healthcare")
        print(report.summary_text())
    """

    def __init__(
        self,
        agent_callable: AgentResponseCallable,
        agent_name: str = "Agent Under Test",
        evaluator: ScenarioEvaluator | None = None,
    ) -> None:
        self._agent = agent_callable
        self._agent_name = agent_name
        self._evaluator = evaluator if evaluator is not None else ScenarioEvaluator()
        self._library = ScenarioLibrary()

    def run_scenarios(
        self,
        scenarios: list[BenchmarkScenario],
    ) -> BenchmarkReport:
        """Run a specified list of scenarios and return a :class:`BenchmarkReport`.

        Parameters
        ----------
        scenarios:
            The :class:`BenchmarkScenario` objects to evaluate.

        Returns
        -------
        BenchmarkReport
        """
        run_id = datetime.now(tz=timezone.utc).isoformat()
        results: list[ScenarioResult] = []

        for scenario in scenarios:
            response = self._agent(scenario.user_input)
            result = self._evaluator.evaluate(scenario, response)
            results.append(result)

        return self._build_report(run_id, results)

    def run_domain(self, domain: str) -> BenchmarkReport:
        """Run all scenarios for a specific domain.

        Parameters
        ----------
        domain:
            Domain identifier (e.g. ``"healthcare"``).

        Returns
        -------
        BenchmarkReport
        """
        scenarios = self._library.for_domain(domain)
        return self.run_scenarios(scenarios)

    def run_all(self) -> BenchmarkReport:
        """Run all 40 benchmark scenarios across all domains.

        Returns
        -------
        BenchmarkReport
        """
        return self.run_scenarios(self._library.all_scenarios())

    def run_by_difficulty(self, difficulty: str) -> BenchmarkReport:
        """Run all scenarios of a specific difficulty level.

        Parameters
        ----------
        difficulty:
            One of ``"easy"``, ``"medium"``, or ``"hard"``.

        Returns
        -------
        BenchmarkReport
        """
        scenarios = self._library.by_difficulty(difficulty)
        return self.run_scenarios(scenarios)

    def run_by_tier(self, tier: RiskTier) -> BenchmarkReport:
        """Run all scenarios at a specific risk tier.

        Parameters
        ----------
        tier:
            The :class:`~agent_vertical.certification.risk_tier.RiskTier`.

        Returns
        -------
        BenchmarkReport
        """
        scenarios = self._library.by_risk_tier(tier)
        return self.run_scenarios(scenarios)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_report(
        self,
        run_id: str,
        results: list[ScenarioResult],
    ) -> BenchmarkReport:
        """Aggregate :class:`ScenarioResult` objects into a :class:`BenchmarkReport`."""
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count

        overall_pass_rate = passed_count / total if total > 0 else 0.0
        overall_avg_score = sum(r.score for r in results) / total if total > 0 else 0.0

        failed_ids = [r.scenario_id for r in results if not r.passed]

        # Build per-domain summaries
        domain_map: dict[str, list[ScenarioResult]] = {}
        for result in results:
            domain_map.setdefault(result.domain, []).append(result)

        domain_summaries: list[DomainBenchmarkSummary] = []
        for domain, domain_results in domain_map.items():
            domain_total = len(domain_results)
            domain_passed = sum(1 for r in domain_results if r.passed)
            domain_failed = domain_total - domain_passed
            domain_pass_rate = domain_passed / domain_total if domain_total > 0 else 0.0
            domain_avg = (
                sum(r.score for r in domain_results) / domain_total if domain_total > 0 else 0.0
            )

            # By difficulty breakdown
            by_difficulty: dict[str, float] = {}
            for difficulty in ("easy", "medium", "hard"):
                diff_results = [r for r in domain_results if r.difficulty == difficulty]
                if diff_results:
                    by_difficulty[difficulty] = sum(
                        1 for r in diff_results if r.passed
                    ) / len(diff_results)

            domain_summaries.append(
                DomainBenchmarkSummary(
                    domain=domain,
                    total_scenarios=domain_total,
                    passed_scenarios=domain_passed,
                    failed_scenarios=domain_failed,
                    pass_rate=domain_pass_rate,
                    average_score=domain_avg,
                    by_difficulty=by_difficulty,
                )
            )

        return BenchmarkReport(
            run_id=run_id,
            agent_name=self._agent_name,
            total_scenarios=total,
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            overall_pass_rate=overall_pass_rate,
            overall_average_score=overall_avg_score,
            domain_summaries=domain_summaries,
            scenario_results=results,
            failed_scenario_ids=failed_ids,
        )
