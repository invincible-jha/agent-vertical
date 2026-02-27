"""Healthcare agent configuration with HIPAA-aware defaults.

HealthcareAgentConfig provides a production-ready dataclass for configuring
healthcare domain agents. It bundles model settings, safety rule references,
compliance framework identifiers, monitoring configuration, and escalation
policies appropriate for HIPAA-regulated environments.

All defaults are conservative and erring toward safety. Operators must
review and validate before deployment in any clinical environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

HealthcareRiskLevel = Literal["informational", "advisory", "decision_support"]
EscalationChannel = Literal["human_review", "emergency_services", "clinical_staff", "none"]


# ---------------------------------------------------------------------------
# Supporting config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MonitoringConfig:
    """Production monitoring configuration for agent deployments.

    Attributes
    ----------
    enable_audit_trail:
        Whether all agent interactions are written to an immutable audit log.
    enable_pii_scan:
        Whether outputs are scanned for inadvertently included PHI/PII.
    enable_latency_alerts:
        Whether latency SLO breaches trigger alerts.
    latency_slo_ms:
        Target maximum latency in milliseconds before alert fires.
    enable_safety_rule_tracing:
        Whether safety rule evaluations are traced and logged.
    alert_channel:
        Destination for alerts (e.g. "pagerduty", "slack", "email").
    """

    enable_audit_trail: bool = True
    enable_pii_scan: bool = True
    enable_latency_alerts: bool = True
    latency_slo_ms: int = 5_000
    enable_safety_rule_tracing: bool = True
    alert_channel: str = "pagerduty"


@dataclass(frozen=True)
class EscalationPolicy:
    """Escalation routing policy for healthcare agents.

    Attributes
    ----------
    primary_channel:
        The first escalation channel to use when escalation is triggered.
    fallback_channel:
        Backup channel if primary is unavailable.
    emergency_trigger_keywords:
        Keywords whose presence in user input triggers emergency escalation.
    require_human_confirmation:
        Whether an action above the advisory risk level needs human sign-off.
    max_advisory_rounds:
        How many advisory back-and-forth turns before forcing escalation.
    """

    primary_channel: EscalationChannel = "clinical_staff"
    fallback_channel: EscalationChannel = "human_review"
    emergency_trigger_keywords: tuple[str, ...] = (
        "chest pain",
        "difficulty breathing",
        "stroke",
        "unconscious",
        "severe bleeding",
        "anaphylaxis",
        "overdose",
        "suicide",
    )
    require_human_confirmation: bool = True
    max_advisory_rounds: int = 3


# ---------------------------------------------------------------------------
# HealthcareAgentConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthcareAgentConfig:
    """Production-ready configuration for a HIPAA-aware healthcare agent.

    Attributes
    ----------
    agent_name:
        Human-readable identifier for this agent instance.
    risk_level:
        Operational risk tier for this agent.
    model_name:
        Abstract model identifier — resolved by the provider abstraction layer.
    model_provider:
        Provider name (e.g. "anthropic", "openai"). Never hardcoded in requests.
    max_output_tokens:
        Hard cap on generated output length to control cost and response scope.
    temperature:
        Sampling temperature. Defaults to 0.1 for consistency in clinical contexts.
    safety_rules_path:
        Path to the HIPAA safety rules YAML file.
    clinical_guardrails_path:
        Path to the clinical guardrails YAML file.
    compliance_framework:
        Identifier for the compliance framework this agent is certified against.
    required_certifications:
        Tuple of certification IDs that must pass before deployment.
    monitoring:
        Production monitoring configuration.
    escalation_policy:
        Escalation routing policy.
    enable_phi_redaction:
        Whether to run PHI redaction on all outbound responses.
    audit_retention_days:
        Number of days to retain audit log entries before rotation.
    """

    agent_name: str
    risk_level: HealthcareRiskLevel = "informational"
    model_name: str = "provider-default"
    model_provider: str = "anthropic"
    max_output_tokens: int = 2_048
    temperature: float = 0.1
    safety_rules_path: str = str(
        Path(__file__).parent / "safety" / "hipaa_rules.yaml"
    )
    clinical_guardrails_path: str = str(
        Path(__file__).parent / "safety" / "clinical_guardrails.yaml"
    )
    compliance_framework: str = "HIPAA-2013"
    required_certifications: tuple[str, ...] = (
        "healthcare.phi_handling",
        "healthcare.hipaa_disclaimer",
        "healthcare.scope_limitation",
        "healthcare.audit_trail",
        "generic.input_validation",
        "generic.output_grounding",
    )
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    escalation_policy: EscalationPolicy = field(default_factory=EscalationPolicy)
    enable_phi_redaction: bool = True
    audit_retention_days: int = 2_555  # 7 years per HIPAA requirement

    def __post_init__(self) -> None:
        """Validate field constraints after construction."""
        if not self.agent_name:
            raise ValueError("HealthcareAgentConfig.agent_name must not be empty.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"HealthcareAgentConfig.temperature must be in [0.0, 2.0]; "
                f"got {self.temperature!r}."
            )
        if self.max_output_tokens < 1:
            raise ValueError(
                f"HealthcareAgentConfig.max_output_tokens must be >= 1; "
                f"got {self.max_output_tokens!r}."
            )
        if self.audit_retention_days < 365:
            raise ValueError(
                "HealthcareAgentConfig.audit_retention_days must be >= 365 "
                "(minimum 1 year for regulatory compliance)."
            )

    def safety_rules_exist(self) -> bool:
        """Return True if the safety_rules_path file exists on disk."""
        return os.path.isfile(self.safety_rules_path)

    def clinical_guardrails_exist(self) -> bool:
        """Return True if the clinical_guardrails_path file exists on disk."""
        return os.path.isfile(self.clinical_guardrails_path)

    def is_phi_protected(self) -> bool:
        """Return True when PHI protection measures are all active."""
        return (
            self.enable_phi_redaction
            and self.monitoring.enable_pii_scan
            and self.monitoring.enable_audit_trail
        )

    def to_dict(self) -> dict[str, object]:
        """Serialise config to a plain dict for structured logging or export."""
        return {
            "agent_name": self.agent_name,
            "risk_level": self.risk_level,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "compliance_framework": self.compliance_framework,
            "required_certifications": list(self.required_certifications),
            "enable_phi_redaction": self.enable_phi_redaction,
            "audit_retention_days": self.audit_retention_days,
            "monitoring": {
                "enable_audit_trail": self.monitoring.enable_audit_trail,
                "enable_pii_scan": self.monitoring.enable_pii_scan,
                "enable_latency_alerts": self.monitoring.enable_latency_alerts,
                "latency_slo_ms": self.monitoring.latency_slo_ms,
                "alert_channel": self.monitoring.alert_channel,
            },
            "escalation_policy": {
                "primary_channel": self.escalation_policy.primary_channel,
                "fallback_channel": self.escalation_policy.fallback_channel,
                "require_human_confirmation": self.escalation_policy.require_human_confirmation,
                "max_advisory_rounds": self.escalation_policy.max_advisory_rounds,
            },
        }


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def build_healthcare_config(
    agent_name: str,
    risk_level: HealthcareRiskLevel = "informational",
    model_provider: str = "anthropic",
    enable_phi_redaction: bool = True,
    alert_channel: str = "pagerduty",
) -> HealthcareAgentConfig:
    """Build a HealthcareAgentConfig with sensible production defaults.

    Parameters
    ----------
    agent_name:
        Human-readable agent name.
    risk_level:
        Operational risk tier. Higher tiers enable stricter guardrails.
    model_provider:
        Provider name passed to the provider abstraction layer.
    enable_phi_redaction:
        Enable PHI redaction on all outbound responses.
    alert_channel:
        Monitoring alert destination.

    Returns
    -------
    HealthcareAgentConfig
        Fully configured healthcare agent config.
    """
    monitoring = MonitoringConfig(
        enable_audit_trail=True,
        enable_pii_scan=True,
        enable_latency_alerts=True,
        latency_slo_ms=5_000,
        enable_safety_rule_tracing=True,
        alert_channel=alert_channel,
    )
    escalation = EscalationPolicy(
        primary_channel="clinical_staff",
        fallback_channel="human_review",
        require_human_confirmation=(risk_level in ("advisory", "decision_support")),
    )
    return HealthcareAgentConfig(
        agent_name=agent_name,
        risk_level=risk_level,
        model_provider=model_provider,
        enable_phi_redaction=enable_phi_redaction,
        monitoring=monitoring,
        escalation_policy=escalation,
    )
