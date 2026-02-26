"""Certification scorer — compute a 0-100 certification score from checklist results.

The scorer weights findings by severity and applies tier-specific penalties
to produce a final score that reflects both the raw pass/fail ratio and the
severity of any failures encountered during evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FindingSeverity(str, Enum):
    """Severity of a single certification finding."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class CheckResult:
    """Result of running a single certification check.

    Attributes
    ----------
    check_id:
        Unique identifier for the check (e.g. ``"hipaa.phi_handling"``).
    check_name:
        Human-readable name.
    passed:
        Whether the check passed.
    severity:
        Severity of the finding when the check fails.
    description:
        Short description of what the check evaluated.
    detail:
        Optional extra detail explaining why the check passed or failed.
    """

    check_id: str
    check_name: str
    passed: bool
    severity: FindingSeverity
    description: str
    detail: str = ""


@dataclass
class ScoringResult:
    """Output of :class:`CertificationScorer`.

    Attributes
    ----------
    score:
        Integer score in the range [0, 100].
    total_checks:
        Number of checks that were evaluated.
    passed_checks:
        Number of checks that passed.
    failed_checks:
        Number of checks that failed.
    critical_failures:
        Number of CRITICAL-severity failures.
    high_failures:
        Number of HIGH-severity failures.
    medium_failures:
        Number of MEDIUM-severity failures.
    low_failures:
        Number of LOW-severity failures.
    penalty_breakdown:
        Mapping of severity label to total penalty points deducted.
    """

    score: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_failures: int
    high_failures: int
    medium_failures: int
    low_failures: int
    penalty_breakdown: dict[str, float] = field(default_factory=dict)


# Points deducted per failed check, by severity
_SEVERITY_PENALTY: dict[FindingSeverity, float] = {
    FindingSeverity.CRITICAL: 25.0,
    FindingSeverity.HIGH: 12.0,
    FindingSeverity.MEDIUM: 5.0,
    FindingSeverity.LOW: 2.0,
    FindingSeverity.INFO: 0.0,
}


class CertificationScorer:
    """Compute a certification score from a list of :class:`CheckResult` objects.

    The algorithm:

    1. Start at 100 points.
    2. Deduct a weighted penalty for each failed check, proportional to the
       check's severity.
    3. Normalise so that the maximum possible deduction is 100 (i.e. all
       critical checks failing yields 0).
    4. Clamp the result to [0, 100] and round to the nearest integer.

    Parameters
    ----------
    severity_penalties:
        Optional override for the per-severity penalty weights.  Useful for
        domain-specific scoring where, e.g., MEDIUM failures should carry
        more weight.
    """

    def __init__(
        self,
        severity_penalties: dict[FindingSeverity, float] | None = None,
    ) -> None:
        self._penalties: dict[FindingSeverity, float] = (
            severity_penalties if severity_penalties is not None else dict(_SEVERITY_PENALTY)
        )

    def compute(self, results: list[CheckResult]) -> ScoringResult:
        """Compute a :class:`ScoringResult` from a list of check results.

        Parameters
        ----------
        results:
            Every :class:`CheckResult` produced by the evaluation run.

        Returns
        -------
        ScoringResult
            Aggregated score and breakdown of failures.
        """
        if not results:
            return ScoringResult(
                score=100,
                total_checks=0,
                passed_checks=0,
                failed_checks=0,
                critical_failures=0,
                high_failures=0,
                medium_failures=0,
                low_failures=0,
                penalty_breakdown={},
            )

        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_results = [r for r in results if not r.passed]

        # Count by severity
        severity_counts: dict[FindingSeverity, int] = {sev: 0 for sev in FindingSeverity}
        for result in failed_results:
            severity_counts[result.severity] += 1

        # Raw penalty sum
        raw_penalty = sum(
            self._penalties[result.severity] for result in failed_results
        )

        # Maximum possible penalty if every check failed at its own severity
        max_possible_penalty = sum(
            self._penalties[result.severity] for result in results
        )

        # Normalise to [0, 100]
        if max_possible_penalty > 0:
            normalised_penalty = (raw_penalty / max_possible_penalty) * 100.0
        else:
            normalised_penalty = 0.0

        score = int(max(0, min(100, round(100.0 - normalised_penalty))))

        penalty_breakdown = {
            sev.value: self._penalties[sev] * severity_counts[sev]
            for sev in FindingSeverity
            if severity_counts[sev] > 0
        }

        return ScoringResult(
            score=score,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=len(failed_results),
            critical_failures=severity_counts[FindingSeverity.CRITICAL],
            high_failures=severity_counts[FindingSeverity.HIGH],
            medium_failures=severity_counts[FindingSeverity.MEDIUM],
            low_failures=severity_counts[FindingSeverity.LOW],
            penalty_breakdown=penalty_breakdown,
        )
