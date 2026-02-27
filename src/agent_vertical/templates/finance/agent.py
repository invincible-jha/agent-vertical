"""Finance agent configuration with PCI-DSS and SOX-aware defaults.

FinanceAgentConfig provides a production-ready dataclass for configuring
finance domain agents. It bundles model settings, safety rule references,
compliance framework identifiers (PCI-DSS, SOX, SEC), monitoring
configuration, and escalation policies for regulated financial environments.

All defaults are conservative. Operators must validate against their specific
regulatory context before deployment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

FinanceRiskLevel = Literal["informational", "advisory", "decision_support"]
FinanceEscalationChannel = Literal[
    "compliance_officer", "human_analyst", "legal_team", "none"
]
ComplianceFramework = Literal["PCI-DSS-v4", "SOX", "SEC-Reg-BI", "FINRA", "MiFID-II"]


# ---------------------------------------------------------------------------
# Supporting config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinanceMonitoringConfig:
    """Production monitoring configuration for finance agent deployments.

    Attributes
    ----------
    enable_audit_trail:
        Whether all interactions are written to an immutable audit log.
    enable_pii_scan:
        Whether outputs are scanned for inadvertently included PII/PCD.
    enable_latency_alerts:
        Whether latency SLO breaches trigger alerts.
    latency_slo_ms:
        Maximum acceptable latency in milliseconds.
    alert_channel:
        Destination for operational alerts.
    enable_fair_lending_monitor:
        Whether outputs are monitored for fair lending principle violations.
    track_model_decisions:
        Whether model-level decisions are stored for regulatory audit.
    """

    enable_audit_trail: bool = True
    enable_pii_scan: bool = True
    enable_latency_alerts: bool = True
    latency_slo_ms: int = 3_000
    alert_channel: str = "pagerduty"
    enable_fair_lending_monitor: bool = True
    track_model_decisions: bool = True


@dataclass(frozen=True)
class FinanceEscalationPolicy:
    """Escalation routing policy for finance agents.

    Attributes
    ----------
    primary_channel:
        First escalation channel when a trigger occurs.
    fallback_channel:
        Backup channel if primary is unavailable.
    escalation_triggers:
        Conditions that trigger escalation (e.g. high-risk score, dual-review threshold).
    require_dual_review:
        Whether Very High risk decisions require two human reviewers.
    max_automated_rounds:
        Maximum automated back-and-forth before forcing human escalation.
    """

    primary_channel: FinanceEscalationChannel = "human_analyst"
    fallback_channel: FinanceEscalationChannel = "compliance_officer"
    escalation_triggers: tuple[str, ...] = (
        "risk_score_very_high",
        "potential_fraud_signal",
        "protected_class_flag",
        "data_quality_critical",
        "contradicted_model_output",
    )
    require_dual_review: bool = True
    max_automated_rounds: int = 2


# ---------------------------------------------------------------------------
# FinanceAgentConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinanceAgentConfig:
    """Production-ready configuration for a PCI-DSS and SOX-aware finance agent.

    Attributes
    ----------
    agent_name:
        Human-readable identifier for this agent instance.
    risk_level:
        Operational risk tier determining strictness of guardrails.
    model_name:
        Abstract model identifier resolved by the provider abstraction layer.
    model_provider:
        Provider name (e.g. "anthropic", "openai"). Never hardcoded in requests.
    max_output_tokens:
        Hard cap on generated output length.
    temperature:
        Sampling temperature. Low (0.0–0.2) for deterministic financial outputs.
    safety_rules_path:
        Path to the PCI-DSS safety rules YAML file.
    compliance_frameworks:
        Tuple of compliance framework identifiers this agent is certified for.
    required_certifications:
        Certification IDs that must pass before deployment.
    monitoring:
        Production monitoring configuration.
    escalation_policy:
        Escalation routing policy.
    enable_pcd_redaction:
        Whether to redact Payment Card Data from all outbound responses.
    enable_fair_lending_checks:
        Whether fair lending principles are enforced on all decisions.
    audit_retention_days:
        Number of days to retain audit log entries (SOX requires 7 years).
    not_investment_advice_disclaimer:
        Required disclaimer text appended to all advisory outputs.
    """

    agent_name: str
    risk_level: FinanceRiskLevel = "informational"
    model_name: str = "provider-default"
    model_provider: str = "anthropic"
    max_output_tokens: int = 2_048
    temperature: float = 0.0
    safety_rules_path: str = str(
        Path(__file__).parent / "safety" / "pci_rules.yaml"
    )
    compliance_frameworks: tuple[ComplianceFramework, ...] = ("PCI-DSS-v4", "SOX")
    required_certifications: tuple[str, ...] = (
        "finance.not_investment_advice",
        "finance.pii_protection",
        "finance.audit_trail",
        "finance.risk_disclosure",
        "finance.fair_lending",
        "generic.input_validation",
        "generic.output_grounding",
        "generic.rate_limiting",
    )
    monitoring: FinanceMonitoringConfig = field(
        default_factory=FinanceMonitoringConfig
    )
    escalation_policy: FinanceEscalationPolicy = field(
        default_factory=FinanceEscalationPolicy
    )
    enable_pcd_redaction: bool = True
    enable_fair_lending_checks: bool = True
    audit_retention_days: int = 2_555  # 7 years per SOX Section 802
    not_investment_advice_disclaimer: str = (
        "This content is for informational purposes only and does not constitute "
        "investment advice, a solicitation, or an offer to buy or sell any security. "
        "Past performance does not guarantee future results. Consult a registered "
        "investment advisor for personalised advice."
    )

    def __post_init__(self) -> None:
        """Validate field constraints after construction."""
        if not self.agent_name:
            raise ValueError("FinanceAgentConfig.agent_name must not be empty.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"FinanceAgentConfig.temperature must be in [0.0, 2.0]; "
                f"got {self.temperature!r}."
            )
        if self.max_output_tokens < 1:
            raise ValueError(
                f"FinanceAgentConfig.max_output_tokens must be >= 1; "
                f"got {self.max_output_tokens!r}."
            )
        if self.audit_retention_days < 365:
            raise ValueError(
                "FinanceAgentConfig.audit_retention_days must be >= 365 "
                "(minimum 1 year for regulatory compliance)."
            )

    def safety_rules_exist(self) -> bool:
        """Return True if the safety_rules_path file exists on disk."""
        return os.path.isfile(self.safety_rules_path)

    def is_pcd_protected(self) -> bool:
        """Return True when Payment Card Data protection measures are active."""
        return (
            self.enable_pcd_redaction
            and self.monitoring.enable_pii_scan
            and self.monitoring.enable_audit_trail
        )

    def has_compliance_framework(self, framework: str) -> bool:
        """Return True if the given framework is in compliance_frameworks."""
        return framework in self.compliance_frameworks

    def to_dict(self) -> dict[str, object]:
        """Serialise config to a plain dict for structured logging or export."""
        return {
            "agent_name": self.agent_name,
            "risk_level": self.risk_level,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "compliance_frameworks": list(self.compliance_frameworks),
            "required_certifications": list(self.required_certifications),
            "enable_pcd_redaction": self.enable_pcd_redaction,
            "enable_fair_lending_checks": self.enable_fair_lending_checks,
            "audit_retention_days": self.audit_retention_days,
            "monitoring": {
                "enable_audit_trail": self.monitoring.enable_audit_trail,
                "enable_pii_scan": self.monitoring.enable_pii_scan,
                "enable_latency_alerts": self.monitoring.enable_latency_alerts,
                "latency_slo_ms": self.monitoring.latency_slo_ms,
                "alert_channel": self.monitoring.alert_channel,
                "enable_fair_lending_monitor": self.monitoring.enable_fair_lending_monitor,
            },
            "escalation_policy": {
                "primary_channel": self.escalation_policy.primary_channel,
                "fallback_channel": self.escalation_policy.fallback_channel,
                "require_dual_review": self.escalation_policy.require_dual_review,
                "max_automated_rounds": self.escalation_policy.max_automated_rounds,
            },
        }


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def build_finance_config(
    agent_name: str,
    risk_level: FinanceRiskLevel = "informational",
    model_provider: str = "anthropic",
    enable_pcd_redaction: bool = True,
    enable_fair_lending_checks: bool = True,
    alert_channel: str = "pagerduty",
) -> FinanceAgentConfig:
    """Build a FinanceAgentConfig with sensible production defaults.

    Parameters
    ----------
    agent_name:
        Human-readable agent name.
    risk_level:
        Operational risk tier. Higher tiers enable stricter guardrails.
    model_provider:
        Provider name passed to the provider abstraction layer.
    enable_pcd_redaction:
        Enable Payment Card Data redaction on all outbound responses.
    enable_fair_lending_checks:
        Enable fair lending principle enforcement on all decisions.
    alert_channel:
        Monitoring alert destination.

    Returns
    -------
    FinanceAgentConfig
        Fully configured finance agent config.
    """
    monitoring = FinanceMonitoringConfig(
        enable_audit_trail=True,
        enable_pii_scan=True,
        enable_latency_alerts=True,
        latency_slo_ms=3_000,
        alert_channel=alert_channel,
        enable_fair_lending_monitor=enable_fair_lending_checks,
        track_model_decisions=True,
    )
    escalation = FinanceEscalationPolicy(
        primary_channel="human_analyst",
        fallback_channel="compliance_officer",
        require_dual_review=(risk_level == "decision_support"),
    )
    return FinanceAgentConfig(
        agent_name=agent_name,
        risk_level=risk_level,
        model_provider=model_provider,
        enable_pcd_redaction=enable_pcd_redaction,
        enable_fair_lending_checks=enable_fair_lending_checks,
        monitoring=monitoring,
        escalation_policy=escalation,
    )
