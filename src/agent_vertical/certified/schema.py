"""Schema definitions for compliance-certified domain templates.

This module defines the data models used throughout the certified-templates
subsystem.  Pydantic v2 is used for models that must survive serialisation
round-trips (YAML/dict); frozen dataclasses are used for immutable value
objects that are never persisted on their own.

Classes
-------
ComplianceFramework
    Enum of recognised compliance standards.
RiskLevel
    Enum of risk classification levels.
TemplateMetadata
    Pydantic model describing template provenance and classification.
SafetyRule
    Frozen dataclass representing a single regex-backed safety rule.
ToolConfig
    Frozen dataclass representing an agent tool declaration.
EvalBenchmark
    Frozen dataclass representing a single evaluation benchmark specification.
DomainTemplate
    Pydantic model for the full template document — the primary unit of the
    certified-templates subsystem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import yaml
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ComplianceFramework(str, Enum):
    """Recognised compliance and regulatory frameworks."""

    HIPAA = "HIPAA"
    """Health Insurance Portability and Accountability Act."""

    SOX = "SOX"
    """Sarbanes-Oxley Act."""

    GDPR = "GDPR"
    """General Data Protection Regulation."""

    SOC2 = "SOC2"
    """Service Organization Control 2."""

    PCI_DSS = "PCI_DSS"
    """Payment Card Industry Data Security Standard."""

    NONE = "NONE"
    """No specific compliance framework required."""


class RiskLevel(str, Enum):
    """Risk classification levels for a certified template."""

    LOW = "LOW"
    """Minimal risk; informational outputs only."""

    MEDIUM = "MEDIUM"
    """Moderate risk; advisory outputs that may influence decisions."""

    HIGH = "HIGH"
    """High risk; outputs that directly inform consequential decisions."""

    CRITICAL = "CRITICAL"
    """Critical risk; outputs that feed directly into regulated workflows."""


# ---------------------------------------------------------------------------
# Value objects (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SafetyRule:
    """A single safety constraint applied to agent output at runtime.

    The ``check_pattern`` field is a Python regex pattern.  A rule is
    considered *triggered* when the pattern matches the agent response (for
    prohibit-type rules) or fails to match (for require-type rules).  The
    distinction is left to the consuming validator; the dataclass itself is
    pattern-only.

    Attributes
    ----------
    rule_id:
        Unique dot-notation identifier (e.g. ``"hipaa.no_phi_exposure"``).
    description:
        Human-readable description of the constraint.
    severity:
        Impact level: ``"warning"``, ``"error"``, or ``"critical"``.
    check_pattern:
        Python regex pattern used to test agent output.
    """

    rule_id: str
    description: str
    severity: str
    check_pattern: str


@dataclass(frozen=True)
class ToolConfig:
    """Configuration for a single tool available to the agent.

    Attributes
    ----------
    name:
        Machine-readable tool name (e.g. ``"audit_logger"``).
    description:
        Human-readable description of what the tool does.
    required:
        When ``True`` the tool must be wired up before the template is
        considered deployable.
    parameters:
        Parameter schema for the tool — free-form dict for flexibility.
    """

    name: str
    description: str
    required: bool
    parameters: dict[str, object]


@dataclass(frozen=True)
class EvalBenchmark:
    """A single evaluation benchmark specification.

    Attributes
    ----------
    name:
        Short identifier for the benchmark (e.g. ``"phi_redaction_rate"``).
    metric:
        The measurement being tracked (e.g. ``"precision"``, ``"recall"``).
    threshold:
        Minimum acceptable value on a 0.0–1.0 scale.
    description:
        Human-readable description of what this benchmark verifies.
    """

    name: str
    metric: str
    threshold: float
    description: str


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TemplateMetadata(BaseModel):
    """Provenance and classification metadata for a :class:`DomainTemplate`.

    Attributes
    ----------
    name:
        Unique machine-readable template name.
    version:
        Semantic version string (e.g. ``"1.0.0"``).
    domain:
        Domain this template belongs to (e.g. ``"healthcare"``).
    compliance_frameworks:
        Compliance frameworks the template is designed to satisfy.
    risk_level:
        Risk classification for this template.
    description:
        Human-readable description of the template's purpose.
    author:
        Author or team identifier.
    created_at:
        UTC datetime of initial template creation.
    tags:
        Free-form tags for search and filtering.
    """

    model_config = {"frozen": True}

    name: str
    version: str = "1.0.0"
    domain: str
    compliance_frameworks: list[ComplianceFramework] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    description: str
    author: str = "AumOS Contributors"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    tags: list[str] = Field(default_factory=list)


def _serialise_safety_rules(
    rules: list[SafetyRule],
) -> list[dict[str, object]]:
    return [
        {
            "rule_id": r.rule_id,
            "description": r.description,
            "severity": r.severity,
            "check_pattern": r.check_pattern,
        }
        for r in rules
    ]


def _deserialise_safety_rules(
    raw: list[dict[str, object]],
) -> list[SafetyRule]:
    return [
        SafetyRule(
            rule_id=item["rule_id"],
            description=item["description"],
            severity=item["severity"],
            check_pattern=item["check_pattern"],
        )
        for item in raw
    ]


def _serialise_tool_configs(
    tools: list[ToolConfig],
) -> list[dict[str, object]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "required": t.required,
            "parameters": t.parameters,
        }
        for t in tools
    ]


def _deserialise_tool_configs(
    raw: list[dict[str, object]],
) -> list[ToolConfig]:
    return [
        ToolConfig(
            name=item["name"],
            description=item["description"],
            required=item["required"],
            parameters=item.get("parameters", {}),
        )
        for item in raw
    ]


def _serialise_eval_benchmarks(
    benchmarks: list[EvalBenchmark],
) -> list[dict[str, object]]:
    return [
        {
            "name": b.name,
            "metric": b.metric,
            "threshold": b.threshold,
            "description": b.description,
        }
        for b in benchmarks
    ]


def _deserialise_eval_benchmarks(
    raw: list[dict[str, object]],
) -> list[EvalBenchmark]:
    return [
        EvalBenchmark(
            name=item["name"],
            metric=item["metric"],
            threshold=float(item["threshold"]),
            description=item["description"],
        )
        for item in raw
    ]


class DomainTemplate(BaseModel):
    """A compliance-certified, self-describing agent template.

    This is the primary document type in the certified-templates subsystem.
    Each instance bundles everything needed to deploy, validate, and audit
    an agent in a regulated domain:

    - A system prompt scoped to the use case.
    - Tool declarations with required/optional flags.
    - Safety rules with compiled-checked regex patterns.
    - Evaluation benchmarks with numeric pass/fail thresholds.
    - Governance policies as a free-form dict.
    - Compliance evidence stubs mapping framework names to prose descriptions.

    Attributes
    ----------
    metadata:
        Provenance and classification metadata.
    system_prompt:
        Full system prompt for the LLM context.
    tool_configs:
        Tool declarations.
    safety_rules:
        Runtime safety constraints with regex patterns.
    governance_policies:
        Free-form governance policies (key→value).
    eval_benchmarks:
        Evaluation benchmarks with numeric thresholds.
    compliance_evidence:
        Mapping of framework name (e.g. ``"HIPAA"``) to an evidence stub
        describing how the template satisfies that framework.
    """

    metadata: TemplateMetadata
    system_prompt: str
    tool_configs: list[ToolConfig] = Field(default_factory=list)
    safety_rules: list[SafetyRule] = Field(default_factory=list)
    governance_policies: dict[str, object] = Field(default_factory=dict)
    eval_benchmarks: list[EvalBenchmark] = Field(default_factory=list)
    compliance_evidence: dict[str, str] = Field(default_factory=dict)

    @field_validator("system_prompt")
    @classmethod
    def system_prompt_not_empty(cls, value: str) -> str:
        """Ensure the system prompt is non-empty."""
        if not value.strip():
            raise ValueError("system_prompt must not be empty")
        return value

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain Python dictionary.

        The returned dict is safe for JSON/YAML serialisation.  Dataclass
        value objects (SafetyRule, ToolConfig, EvalBenchmark) are converted
        to dicts; datetime values are ISO-formatted strings.

        Returns
        -------
        dict[str, object]
        """
        metadata_dict: dict[str, object] = {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "domain": self.metadata.domain,
            "compliance_frameworks": [f.value for f in self.metadata.compliance_frameworks],
            "risk_level": self.metadata.risk_level.value,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "created_at": self.metadata.created_at.isoformat(),
            "tags": list(self.metadata.tags),
        }
        return {
            "metadata": metadata_dict,
            "system_prompt": self.system_prompt,
            "tool_configs": _serialise_tool_configs(self.tool_configs),
            "safety_rules": _serialise_safety_rules(self.safety_rules),
            "governance_policies": dict(self.governance_policies),
            "eval_benchmarks": _serialise_eval_benchmarks(self.eval_benchmarks),
            "compliance_evidence": dict(self.compliance_evidence),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DomainTemplate":
        """Deserialise from a plain Python dictionary.

        Parameters
        ----------
        data:
            Dictionary as produced by :meth:`to_dict`.

        Returns
        -------
        DomainTemplate
        """
        raw_meta = data["metadata"]
        created_at_raw = raw_meta.get("created_at")
        if isinstance(created_at_raw, str):
            created_at = datetime.fromisoformat(created_at_raw)
        elif isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        else:
            created_at = datetime.now(tz=timezone.utc)

        metadata = TemplateMetadata(
            name=raw_meta["name"],
            version=raw_meta.get("version", "1.0.0"),
            domain=raw_meta["domain"],
            compliance_frameworks=[
                ComplianceFramework(f) for f in raw_meta.get("compliance_frameworks", [])
            ],
            risk_level=RiskLevel(raw_meta.get("risk_level", RiskLevel.MEDIUM.value)),
            description=raw_meta["description"],
            author=raw_meta.get("author", "AumOS Contributors"),
            created_at=created_at,
            tags=raw_meta.get("tags", []),
        )
        return cls(
            metadata=metadata,
            system_prompt=data["system_prompt"],
            tool_configs=_deserialise_tool_configs(data.get("tool_configs", [])),
            safety_rules=_deserialise_safety_rules(data.get("safety_rules", [])),
            governance_policies=data.get("governance_policies", {}),
            eval_benchmarks=_deserialise_eval_benchmarks(data.get("eval_benchmarks", [])),
            compliance_evidence=data.get("compliance_evidence", {}),
        )

    def to_yaml(self) -> str:
        """Serialise to a YAML string.

        Returns
        -------
        str
            YAML document representing this template.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "DomainTemplate":
        """Deserialise from a YAML string.

        Parameters
        ----------
        yaml_text:
            YAML document as produced by :meth:`to_yaml`.

        Returns
        -------
        DomainTemplate
        """
        data: dict[str, object] = yaml.safe_load(yaml_text)
        return cls.from_dict(data)

    def validate_template(self) -> list[str]:
        """Return a list of validation warnings for this template.

        This is a lightweight self-check that does not raise exceptions;
        it returns a list of human-readable warning strings.  For a full
        structured validation result use :class:`~agent_vertical.certified.validator.TemplateValidator`.

        Returns
        -------
        list[str]
            Zero or more warning strings.  Empty list means no issues found.
        """
        warnings: list[str] = []

        if not self.tool_configs:
            warnings.append("Template has no tool configurations.")

        if not self.safety_rules:
            warnings.append("Template has no safety rules.")

        if not self.eval_benchmarks:
            warnings.append("Template has no evaluation benchmarks.")

        if not self.compliance_evidence:
            warnings.append("Template has no compliance evidence stubs.")

        if len(self.system_prompt.strip()) < 50:
            warnings.append("System prompt is very short (< 50 characters).")

        for rule in self.safety_rules:
            if rule.severity not in {"warning", "error", "critical"}:
                warnings.append(
                    f"Safety rule '{rule.rule_id}' has unrecognised severity "
                    f"'{rule.severity}'. Expected: warning, error, critical."
                )
            try:
                re.compile(rule.check_pattern)
            except re.error as exc:
                warnings.append(
                    f"Safety rule '{rule.rule_id}' has invalid regex pattern: {exc}"
                )

        for benchmark in self.eval_benchmarks:
            if not 0.0 <= benchmark.threshold <= 1.0:
                warnings.append(
                    f"Benchmark '{benchmark.name}' threshold {benchmark.threshold} "
                    "is outside the valid range [0.0, 1.0]."
                )

        return warnings
