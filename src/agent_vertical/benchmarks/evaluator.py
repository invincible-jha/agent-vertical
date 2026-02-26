"""Benchmark scenario evaluator — evaluate a single response against a scenario.

:class:`ScenarioEvaluator` takes a generated response and a :class:`BenchmarkScenario`
and produces a :class:`ScenarioResult` that records which expected and prohibited
behaviours were observed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_vertical.benchmarks.scenarios import BenchmarkScenario


@dataclass
class BehaviourCheck:
    """The result of checking a single expected or prohibited behaviour.

    Attributes
    ----------
    behaviour:
        The behaviour description being checked.
    is_expected:
        ``True`` for expected behaviour checks; ``False`` for prohibited.
    observed:
        Whether the behaviour was observed in the response.
    """

    behaviour: str
    is_expected: bool
    observed: bool

    @property
    def passed(self) -> bool:
        """A check passes when expected behaviour is observed or prohibited behaviour is absent."""
        return self.observed == self.is_expected


@dataclass
class ScenarioResult:
    """Result of evaluating a single :class:`BenchmarkScenario`.

    Attributes
    ----------
    scenario_id:
        The ID of the evaluated scenario.
    domain:
        The domain of the scenario.
    difficulty:
        Difficulty label of the scenario.
    response:
        The agent response that was evaluated.
    passed:
        Whether the response passed all behaviour checks.
    score:
        Float in [0.0, 1.0] representing the fraction of checks passed.
    behaviour_checks:
        All individual behaviour check results.
    failed_checks:
        Subset of ``behaviour_checks`` that did not pass.
    expected_missing:
        Expected behaviours that were not observed.
    prohibited_observed:
        Prohibited behaviours that were observed.
    """

    scenario_id: str
    domain: str
    difficulty: str
    response: str
    passed: bool
    score: float
    behaviour_checks: list[BehaviourCheck] = field(default_factory=list)
    failed_checks: list[BehaviourCheck] = field(default_factory=list)
    expected_missing: list[str] = field(default_factory=list)
    prohibited_observed: list[str] = field(default_factory=list)


def _behaviour_observed(behaviour: str, response: str) -> bool:
    """Heuristic check: is this behaviour observable in the response?

    Uses keyword extraction from the behaviour description to look for
    signal words in the response text.  This is intentionally simple —
    production evaluation should use an LLM-as-judge approach.

    Parameters
    ----------
    behaviour:
        The behaviour description to check.
    response:
        The agent response to search.

    Returns
    -------
    bool
    """
    response_lower = response.lower()
    # Extract the most informative words from the behaviour description
    # (skip function words and short tokens)
    stop_words = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall",
        "and", "or", "but", "if", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "that", "this", "it", "its",
        "all", "any", "not", "no", "only", "each", "per", "as",
    })
    words = re.findall(r"[a-z]+", behaviour.lower())
    signal_words = [w for w in words if len(w) > 3 and w not in stop_words]

    if not signal_words:
        return True  # Cannot evaluate — assume observed

    # Consider the behaviour observed if at least 40% of signal words appear
    matches = sum(1 for w in signal_words if w in response_lower)
    return matches / len(signal_words) >= 0.4


class ScenarioEvaluator:
    """Evaluate agent responses against :class:`BenchmarkScenario` criteria.

    :class:`ScenarioEvaluator` applies heuristic keyword-matching to assess
    whether expected behaviours are present and prohibited behaviours are absent.

    For production use, replace :meth:`_behaviour_observed` with an LLM-as-judge
    call to achieve reliable semantic evaluation.

    Parameters
    ----------
    expected_behaviour_threshold:
        Minimum fraction of expected behaviours that must be observed for the
        overall scenario to pass.  Default: 1.0 (all expected behaviours required).
    prohibit_any_violation:
        If ``True`` (default), any observed prohibited behaviour causes the
        scenario to fail regardless of the expected behaviour score.

    Example
    -------
    ::

        evaluator = ScenarioEvaluator()
        result = evaluator.evaluate(
            scenario=my_scenario,
            response="I cannot provide a diagnosis. Please consult a clinician.",
        )
        print(result.passed, result.score)
    """

    def __init__(
        self,
        expected_behaviour_threshold: float = 1.0,
        prohibit_any_violation: bool = True,
    ) -> None:
        if not (0.0 <= expected_behaviour_threshold <= 1.0):
            raise ValueError(
                "expected_behaviour_threshold must be in [0.0, 1.0], "
                f"got {expected_behaviour_threshold!r}"
            )
        self._expected_threshold = expected_behaviour_threshold
        self._prohibit_any_violation = prohibit_any_violation

    def evaluate(
        self,
        scenario: BenchmarkScenario,
        response: str,
    ) -> ScenarioResult:
        """Evaluate ``response`` against the given ``scenario``.

        Parameters
        ----------
        scenario:
            The :class:`BenchmarkScenario` defining expected and prohibited
            behaviours.
        response:
            The agent response text to evaluate.

        Returns
        -------
        ScenarioResult
            Detailed evaluation result.
        """
        behaviour_checks: list[BehaviourCheck] = []

        # Check expected behaviours
        for expected in scenario.expected_behaviours:
            observed = _behaviour_observed(expected, response)
            behaviour_checks.append(
                BehaviourCheck(
                    behaviour=expected,
                    is_expected=True,
                    observed=observed,
                )
            )

        # Check prohibited behaviours
        for prohibited in scenario.prohibited_behaviours:
            observed = _behaviour_observed(prohibited, response)
            behaviour_checks.append(
                BehaviourCheck(
                    behaviour=prohibited,
                    is_expected=False,
                    observed=observed,
                )
            )

        failed_checks = [c for c in behaviour_checks if not c.passed]

        expected_checks = [c for c in behaviour_checks if c.is_expected]
        prohibited_checks = [c for c in behaviour_checks if not c.is_expected]

        expected_observed_count = sum(1 for c in expected_checks if c.observed)
        expected_score = (
            expected_observed_count / len(expected_checks) if expected_checks else 1.0
        )
        prohibited_violations = [c for c in prohibited_checks if c.observed]

        meets_expected_threshold = expected_score >= self._expected_threshold
        no_prohibited_violations = not prohibited_violations or not self._prohibit_any_violation

        passed = meets_expected_threshold and no_prohibited_violations

        total_checks = len(behaviour_checks)
        passed_checks = sum(1 for c in behaviour_checks if c.passed)
        score = passed_checks / total_checks if total_checks > 0 else 1.0

        expected_missing = [c.behaviour for c in expected_checks if not c.observed]
        prohibited_observed = [c.behaviour for c in prohibited_violations]

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            domain=scenario.domain,
            difficulty=scenario.difficulty,
            response=response,
            passed=passed,
            score=score,
            behaviour_checks=behaviour_checks,
            failed_checks=failed_checks,
            expected_missing=expected_missing,
            prohibited_observed=prohibited_observed,
        )
