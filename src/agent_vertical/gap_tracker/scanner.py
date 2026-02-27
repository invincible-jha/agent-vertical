"""Gap tracker for vertical agent templates.

Scans a template configuration dict against a set of expected fields and
best-practice patterns to identify gaps — missing, incomplete, or
sub-standard configuration items that should be addressed before the
template is deployed in production.

Each gap is classified by severity and mapped to a remediation suggestion.
A :class:`GapReport` summarises all discovered gaps and provides an
overall completion score.

Design
------
- Gap rules are plain functions: ``(config) -> TemplateGap | None``.
- The scanner collects gaps from all registered rule functions.
- Rules are domain-agnostic by default; domain-specific rules can be
  registered with ``TemplateGapScanner.register_rule``.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# Gap severity
# ---------------------------------------------------------------------------


class GapSeverity(str, Enum):
    """Severity classification for a template gap."""

    CRITICAL = "critical"   # Deployment-blocking; must be fixed
    HIGH = "high"           # Significant risk; should be fixed before go-live
    MEDIUM = "medium"       # Best-practice gap; fix in next iteration
    LOW = "low"             # Minor improvement; fix when convenient
    INFO = "info"           # Informational only; no action required


# ---------------------------------------------------------------------------
# Template gap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateGap:
    """A single gap discovered during template scanning.

    Attributes
    ----------
    gap_id:
        Unique identifier for this gap type (e.g. ``"missing.disclaimer"``).
    title:
        Short human-readable title.
    description:
        Detailed description of the gap and its implications.
    severity:
        How critical this gap is.
    remediation:
        Actionable steps to close the gap.
    field_path:
        Dot-notation path to the missing or incomplete field (if applicable).
    """

    gap_id: str
    title: str
    description: str
    severity: GapSeverity
    remediation: str
    field_path: str = ""


# ---------------------------------------------------------------------------
# Gap report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GapReport:
    """Summary of all gaps found during a template scan.

    Attributes
    ----------
    template_identifier:
        Name or ID of the scanned template.
    gaps:
        All gaps discovered, in order of severity (critical first).
    completion_score:
        0-100 score reflecting how complete the template is (100 = no gaps).
    scanned_at:
        UTC timestamp of when the scan was performed.
    total_rules_run:
        Number of rules evaluated during the scan.
    """

    template_identifier: str
    gaps: tuple[TemplateGap, ...]
    completion_score: float
    scanned_at: datetime.datetime
    total_rules_run: int

    @property
    def critical_gaps(self) -> list[TemplateGap]:
        """Return all CRITICAL-severity gaps."""
        return [g for g in self.gaps if g.severity == GapSeverity.CRITICAL]

    @property
    def high_gaps(self) -> list[TemplateGap]:
        """Return all HIGH-severity gaps."""
        return [g for g in self.gaps if g.severity == GapSeverity.HIGH]

    @property
    def is_deployment_ready(self) -> bool:
        """Return True when there are no CRITICAL gaps."""
        return len(self.critical_gaps) == 0

    @property
    def gap_count(self) -> int:
        """Return the total number of discovered gaps."""
        return len(self.gaps)

    def gaps_by_severity(self) -> dict[str, list[TemplateGap]]:
        """Return gaps grouped by severity level.

        Returns
        -------
        dict[str, list[TemplateGap]]
            Mapping from severity string to list of gaps.
        """
        grouped: dict[str, list[TemplateGap]] = {sev.value: [] for sev in GapSeverity}
        for gap in self.gaps:
            grouped[gap.severity.value].append(gap)
        return grouped


# ---------------------------------------------------------------------------
# Rule type alias
# ---------------------------------------------------------------------------

GapRule = Callable[[dict[str, object]], TemplateGap | None]


# ---------------------------------------------------------------------------
# Built-in gap rules
# ---------------------------------------------------------------------------


def _rule_missing_disclaimer(config: dict[str, object]) -> TemplateGap | None:
    if not config.get("disclaimer"):
        return TemplateGap(
            gap_id="missing.disclaimer",
            title="Missing Disclaimer",
            description=(
                "The template does not include a disclaimer statement. "
                "All vertical agent templates must carry a disclaimer informing "
                "users that output is not professional advice."
            ),
            severity=GapSeverity.CRITICAL,
            remediation="Add a 'disclaimer' field with a clear not-advice statement.",
            field_path="disclaimer",
        )
    return None


def _rule_missing_domain(config: dict[str, object]) -> TemplateGap | None:
    if not config.get("domain"):
        return TemplateGap(
            gap_id="missing.domain",
            title="Missing Domain",
            description=(
                "The template does not declare its operational domain. "
                "Domain classification is required for certification and "
                "compliance-requirement selection."
            ),
            severity=GapSeverity.HIGH,
            remediation="Add a 'domain' field (e.g. 'healthcare', 'finance', 'legal').",
            field_path="domain",
        )
    return None


def _rule_missing_risk_tier(config: dict[str, object]) -> TemplateGap | None:
    valid = {"informational", "advisory", "decision_support"}
    tier = str(config.get("risk_tier", "")).lower()
    if tier not in valid:
        return TemplateGap(
            gap_id="missing.risk_tier",
            title="Missing or Invalid Risk Tier",
            description=(
                "The template does not declare a valid risk tier. "
                "Risk tier determines which certification requirements apply."
            ),
            severity=GapSeverity.HIGH,
            remediation=(
                "Set 'risk_tier' to one of: 'informational', 'advisory', "
                "'decision_support'."
            ),
            field_path="risk_tier",
        )
    return None


def _rule_missing_version(config: dict[str, object]) -> TemplateGap | None:
    import re
    version = config.get("version", "")
    pattern = re.compile(r"^\d+\.\d+\.\d+$")
    if not (isinstance(version, str) and pattern.match(version)):
        return TemplateGap(
            gap_id="missing.version",
            title="Missing or Invalid Version",
            description=(
                "The template does not declare a valid semantic version. "
                "Versioning is required for template lifecycle management."
            ),
            severity=GapSeverity.MEDIUM,
            remediation="Set 'version' to a semantic version string (e.g. '1.0.0').",
            field_path="version",
        )
    return None


def _rule_missing_input_validation(config: dict[str, object]) -> TemplateGap | None:
    if not config.get("input_validation"):
        return TemplateGap(
            gap_id="missing.input_validation",
            title="Missing Input Validation Configuration",
            description=(
                "The template does not declare input validation. "
                "Without input validation, the agent is vulnerable to prompt "
                "injection and excessive input attacks."
            ),
            severity=GapSeverity.HIGH,
            remediation=(
                "Add an 'input_validation' configuration block specifying "
                "max length, allowed content types, and sanitisation rules."
            ),
            field_path="input_validation",
        )
    return None


def _rule_missing_rate_limiting(config: dict[str, object]) -> TemplateGap | None:
    if not config.get("rate_limiting"):
        return TemplateGap(
            gap_id="missing.rate_limiting",
            title="Missing Rate Limiting Configuration",
            description=(
                "The template does not declare rate limiting. "
                "Without rate limits, the agent endpoint is vulnerable to "
                "abuse and uncontrolled cost growth."
            ),
            severity=GapSeverity.MEDIUM,
            remediation=(
                "Add a 'rate_limiting' configuration block specifying "
                "per-user and per-organisation limits."
            ),
            field_path="rate_limiting",
        )
    return None


def _rule_missing_sources(config: dict[str, object]) -> TemplateGap | None:
    sources = config.get("sources", [])
    if not (isinstance(sources, list) and len(sources) > 0):
        return TemplateGap(
            gap_id="missing.sources",
            title="No Knowledge Sources Declared",
            description=(
                "The template does not declare any knowledge sources. "
                "Without grounded sources, agent outputs cannot be verified "
                "for accuracy and hallucinations are harder to detect."
            ),
            severity=GapSeverity.HIGH,
            remediation="Add a 'sources' list containing at least one knowledge source identifier.",
            field_path="sources",
        )
    return None


def _rule_missing_audit_trail(config: dict[str, object]) -> TemplateGap | None:
    if not config.get("audit_trail"):
        return TemplateGap(
            gap_id="missing.audit_trail",
            title="Missing Audit Trail Configuration",
            description=(
                "The template does not declare audit trail configuration. "
                "Audit trails are required for compliance and post-incident review."
            ),
            severity=GapSeverity.HIGH,
            remediation=(
                "Add an 'audit_trail' configuration block specifying the "
                "backend, retention period, and field coverage."
            ),
            field_path="audit_trail",
        )
    return None


def _rule_decision_support_missing_human_gate(config: dict[str, object]) -> TemplateGap | None:
    tier = str(config.get("risk_tier", "")).lower()
    if tier == "decision_support" and not config.get("human_review_gate"):
        return TemplateGap(
            gap_id="governance.missing_human_review_gate",
            title="Decision-Support Template Missing Human Review Gate",
            description=(
                "Templates at the 'decision_support' risk tier must include a "
                "human review gate to prevent fully automated decisions that "
                "affect real-world outcomes."
            ),
            severity=GapSeverity.CRITICAL,
            remediation=(
                "Add a 'human_review_gate' configuration block defining the "
                "review workflow, reviewer roles, and timeout policy."
            ),
            field_path="human_review_gate",
        )
    return None


def _rule_short_description(config: dict[str, object]) -> TemplateGap | None:
    description = config.get("description", "")
    if not (isinstance(description, str) and len(description.strip()) >= 50):
        return TemplateGap(
            gap_id="quality.short_description",
            title="Template Description Too Short",
            description=(
                "The template description is absent or fewer than 50 characters. "
                "A meaningful description helps operators understand the template's "
                "purpose and limitations."
            ),
            severity=GapSeverity.LOW,
            remediation="Add a 'description' field of at least 50 characters.",
            field_path="description",
        )
    return None


# ---------------------------------------------------------------------------
# Default rule registry
# ---------------------------------------------------------------------------

_DEFAULT_RULES: list[GapRule] = [
    _rule_missing_disclaimer,
    _rule_missing_domain,
    _rule_missing_risk_tier,
    _rule_missing_version,
    _rule_missing_input_validation,
    _rule_missing_rate_limiting,
    _rule_missing_sources,
    _rule_missing_audit_trail,
    _rule_decision_support_missing_human_gate,
    _rule_short_description,
]

# Severity ordering for sorting
_SEVERITY_ORDER: dict[GapSeverity, int] = {
    GapSeverity.CRITICAL: 0,
    GapSeverity.HIGH: 1,
    GapSeverity.MEDIUM: 2,
    GapSeverity.LOW: 3,
    GapSeverity.INFO: 4,
}

# Score weights per severity (gap penalty contribution)
_SEVERITY_WEIGHT: dict[GapSeverity, float] = {
    GapSeverity.CRITICAL: 25.0,
    GapSeverity.HIGH: 12.0,
    GapSeverity.MEDIUM: 5.0,
    GapSeverity.LOW: 2.0,
    GapSeverity.INFO: 0.0,
}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class TemplateGapScanner:
    """Scans a template configuration dict against gap rules.

    Parameters
    ----------
    extra_rules:
        Additional gap rule functions to include beyond the default set.
    include_defaults:
        When False, only *extra_rules* are used.  Defaults to True.
    """

    def __init__(
        self,
        extra_rules: list[GapRule] | None = None,
        include_defaults: bool = True,
    ) -> None:
        self._rules: list[GapRule] = []
        if include_defaults:
            self._rules.extend(_DEFAULT_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)

    def register_rule(self, rule: GapRule) -> None:
        """Add a custom gap rule to the scanner.

        Parameters
        ----------
        rule:
            A callable ``(config) -> TemplateGap | None``.
        """
        self._rules.append(rule)

    def scan(
        self,
        config: dict[str, object],
        template_identifier: str = "unknown",
    ) -> GapReport:
        """Scan *config* and return a :class:`GapReport`.

        Parameters
        ----------
        config:
            Template or agent configuration dictionary.
        template_identifier:
            Name or ID to include in the report.

        Returns
        -------
        GapReport
            All discovered gaps and a completion score.
        """
        gaps: list[TemplateGap] = []
        for rule in self._rules:
            gap = rule(config)
            if gap is not None:
                gaps.append(gap)

        # Sort by severity
        gaps.sort(key=lambda g: _SEVERITY_ORDER[g.severity])

        completion_score = self._compute_score(gaps)

        return GapReport(
            template_identifier=template_identifier,
            gaps=tuple(gaps),
            completion_score=completion_score,
            scanned_at=datetime.datetime.now(datetime.timezone.utc),
            total_rules_run=len(self._rules),
        )

    def rule_count(self) -> int:
        """Return the number of rules registered with this scanner."""
        return len(self._rules)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_score(self, gaps: list[TemplateGap]) -> float:
        """Compute a 0-100 completion score from discovered gaps.

        Deducts weighted penalties for each gap, normalised so that the
        maximum possible deduction is 100.

        Parameters
        ----------
        gaps:
            List of discovered gaps.

        Returns
        -------
        float
            Score in [0.0, 100.0].
        """
        if not gaps:
            return 100.0

        total_penalty = sum(_SEVERITY_WEIGHT[g.severity] for g in gaps)
        max_possible = sum(_SEVERITY_WEIGHT[sev] for sev in GapSeverity) * len(gaps)

        if max_possible == 0:
            return 100.0

        normalised = (total_penalty / max_possible) * 100.0
        return max(0.0, min(100.0, 100.0 - normalised))


__all__ = [
    "GapReport",
    "GapRule",
    "GapSeverity",
    "TemplateGap",
    "TemplateGapScanner",
]
