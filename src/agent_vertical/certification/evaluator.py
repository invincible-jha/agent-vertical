"""Certification evaluator — run a domain-specific evaluation checklist.

The :class:`CertificationEvaluator` accepts a list of :class:`CheckResult`
objects produced by domain-specific modules and aggregates them into a final
:class:`CertificationResult`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.certification.scorer import (
    CheckResult,
    CertificationScorer,
    FindingSeverity,
    ScoringResult,
)


@dataclass(frozen=True)
class CertificationFinding:
    """A single finding surfaced during certification.

    Attributes
    ----------
    check_id:
        The check that produced this finding.
    severity:
        Severity of the finding.
    message:
        Human-readable explanation.
    remediation:
        Suggested remediation steps.
    """

    check_id: str
    severity: FindingSeverity
    message: str
    remediation: str = ""


@dataclass
class CertificationResult:
    """Full output of a certification evaluation run.

    Attributes
    ----------
    domain:
        The domain that was evaluated (e.g. ``"healthcare"``).
    tier:
        The risk tier at which the agent was evaluated.
    score:
        Integer score in [0, 100].
    passed:
        Whether the agent achieved the minimum passing score for its tier.
    scoring_detail:
        Full :class:`ScoringResult` with per-severity breakdown.
    findings:
        All findings (both passed and failed checks) in order.
    failed_findings:
        Subset of ``findings`` where the check did not pass.
    critical_findings:
        Subset of ``failed_findings`` with CRITICAL severity.
    """

    domain: str
    tier: RiskTier
    score: int
    passed: bool
    scoring_detail: ScoringResult
    findings: list[CertificationFinding] = field(default_factory=list)
    failed_findings: list[CertificationFinding] = field(default_factory=list)
    critical_findings: list[CertificationFinding] = field(default_factory=list)


class DomainCheckProvider(Protocol):
    """Protocol for objects that provide domain-specific check results.

    Domain modules implement this protocol so that :class:`CertificationEvaluator`
    can remain domain-agnostic.
    """

    def run_checks(self) -> list[CheckResult]:
        """Execute all checks and return results."""
        ...


class CertificationEvaluator:
    """Run all domain checks and produce a :class:`CertificationResult`.

    Parameters
    ----------
    domain:
        Domain identifier (e.g. ``"healthcare"``, ``"finance"``).
    tier:
        The :class:`RiskTier` at which to evaluate the agent.  Determines the
        minimum passing score and which checks are mandatory.
    scorer:
        Optional custom :class:`CertificationScorer`.  Defaults to the
        standard scorer with built-in severity weights.

    Example
    -------
    ::

        evaluator = CertificationEvaluator("healthcare", RiskTier.DECISION_SUPPORT)
        check_results = my_healthcare_module.run_checks()
        result = evaluator.evaluate(check_results)
        print(result.score, result.passed)
    """

    def __init__(
        self,
        domain: str,
        tier: RiskTier,
        scorer: CertificationScorer | None = None,
    ) -> None:
        self._domain = domain
        self._tier = tier
        self._scorer = scorer if scorer is not None else CertificationScorer()

    def evaluate(self, check_results: list[CheckResult]) -> CertificationResult:
        """Aggregate check results into a :class:`CertificationResult`.

        Parameters
        ----------
        check_results:
            All :class:`CheckResult` objects from every domain check.

        Returns
        -------
        CertificationResult
            Final certification output including score, pass/fail, and findings.
        """
        scoring_detail: ScoringResult = self._scorer.compute(check_results)
        passed: bool = scoring_detail.score >= self._tier.minimum_passing_score

        all_findings: list[CertificationFinding] = []
        failed_findings: list[CertificationFinding] = []
        critical_findings: list[CertificationFinding] = []

        for check_result in check_results:
            finding = CertificationFinding(
                check_id=check_result.check_id,
                severity=check_result.severity,
                message=(
                    f"{check_result.check_name}: PASSED"
                    if check_result.passed
                    else f"{check_result.check_name}: FAILED — {check_result.detail or check_result.description}"
                ),
                remediation="" if check_result.passed else self._remediation_for(check_result),
            )
            all_findings.append(finding)

            if not check_result.passed:
                failed_findings.append(finding)
                if check_result.severity == FindingSeverity.CRITICAL:
                    critical_findings.append(finding)

        return CertificationResult(
            domain=self._domain,
            tier=self._tier,
            score=scoring_detail.score,
            passed=passed,
            scoring_detail=scoring_detail,
            findings=all_findings,
            failed_findings=failed_findings,
            critical_findings=critical_findings,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _remediation_for(check_result: CheckResult) -> str:
        """Generate a basic remediation hint for a failed check."""
        severity_hints: dict[FindingSeverity, str] = {
            FindingSeverity.CRITICAL: (
                "Immediately halt deployment and escalate to the security/compliance team. "
                "This issue must be resolved before any production use."
            ),
            FindingSeverity.HIGH: (
                "Address this before deployment. Engage the responsible team and "
                "document the remediation steps taken."
            ),
            FindingSeverity.MEDIUM: (
                "Schedule remediation within the current sprint. "
                "Add a compliance tracking ticket."
            ),
            FindingSeverity.LOW: (
                "Add to the backlog for the next maintenance cycle. "
                "Document as a known limitation in the agent's system card."
            ),
            FindingSeverity.INFO: "Review the finding and determine whether action is needed.",
        }
        return severity_hints.get(check_result.severity, "Review and remediate as appropriate.")
