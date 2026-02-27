"""Customer service agent configuration with escalation policy.

CustomerServiceAgentConfig provides a production-ready dataclass for
configuring customer service domain agents. It bundles model settings,
tone constraints, PII handling, escalation routing, and monitoring
configuration for consumer-facing support environments.

Escalation policy defines when and how the agent hands off to a human
agent, including trigger conditions, channel preferences, and context
preservation requirements.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EscalationTrigger = Literal[
    "customer_request",
    "sentiment_negative",
    "unresolved_after_n_turns",
    "high_value_customer",
    "complaint_severity_high",
    "legal_threat",
    "safety_concern",
]
HumanChannel = Literal["live_chat", "phone", "email_ticket", "video_call", "none"]
TonePolicy = Literal["formal", "friendly", "neutral", "empathetic"]


# ---------------------------------------------------------------------------
# Supporting config dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EscalationPolicy:
    """Escalation routing policy for customer service agents.

    Attributes
    ----------
    triggers:
        Tuple of conditions that trigger human escalation.
    primary_channel:
        Preferred channel for human agent handoff.
    fallback_channel:
        Backup channel if primary is unavailable.
    max_turns_before_escalation:
        Maximum number of conversation turns before forcing escalation
        if the issue remains unresolved.
    preserve_context_on_handoff:
        Whether full conversation context is transferred to the human agent.
    escalation_message_template:
        Message sent to the customer when escalation occurs.
    high_value_customer_threshold_usd:
        Customers with lifetime value above this threshold trigger immediate
        escalation rather than standard automated handling.
    """

    triggers: tuple[EscalationTrigger, ...] = (
        "customer_request",
        "sentiment_negative",
        "unresolved_after_n_turns",
        "legal_threat",
        "safety_concern",
        "complaint_severity_high",
    )
    primary_channel: HumanChannel = "live_chat"
    fallback_channel: HumanChannel = "email_ticket"
    max_turns_before_escalation: int = 8
    preserve_context_on_handoff: bool = True
    escalation_message_template: str = (
        "I'm connecting you with one of our specialists who can better assist "
        "you with this. Please hold for a moment while I transfer your conversation."
    )
    high_value_customer_threshold_usd: float = 10_000.0


@dataclass(frozen=True)
class CustomerServiceMonitoringConfig:
    """Monitoring configuration for customer service agent deployments.

    Attributes
    ----------
    enable_sentiment_tracking:
        Whether customer sentiment is tracked per conversation turn.
    enable_csat_collection:
        Whether a CSAT survey is triggered at conversation end.
    enable_audit_trail:
        Whether all interactions are logged.
    enable_pii_scan:
        Whether PII is detected and redacted from logs.
    alert_on_negative_sentiment:
        Whether a sustained negative sentiment trend triggers an alert.
    alert_channel:
        Destination for operational alerts.
    latency_slo_ms:
        Maximum acceptable first-response latency in milliseconds.
    """

    enable_sentiment_tracking: bool = True
    enable_csat_collection: bool = True
    enable_audit_trail: bool = True
    enable_pii_scan: bool = True
    alert_on_negative_sentiment: bool = True
    alert_channel: str = "slack"
    latency_slo_ms: int = 3_000


# ---------------------------------------------------------------------------
# CustomerServiceAgentConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CustomerServiceAgentConfig:
    """Production-ready configuration for a customer service agent.

    Attributes
    ----------
    agent_name:
        Human-readable identifier for this agent instance.
    brand_name:
        The brand name the agent represents. Used in greetings and sign-offs.
    tone_policy:
        Communication tone the agent should maintain throughout interactions.
    model_name:
        Abstract model identifier resolved by the provider abstraction layer.
    model_provider:
        Provider name (e.g. "anthropic", "openai").
    max_output_tokens:
        Hard cap on generated output length.
    temperature:
        Sampling temperature. Moderate (0.3–0.6) for natural conversational tone.
    safety_rules_path:
        Path to the escalation policy YAML file.
    escalation_policy:
        Escalation routing policy configuration.
    monitoring:
        Production monitoring configuration.
    enable_pii_redaction:
        Whether PII is redacted from all logged interactions.
    supported_languages:
        Tuple of BCP-47 language codes the agent is certified to handle.
    max_session_duration_minutes:
        Maximum session length before automatic closure.
    allow_proactive_offers:
        Whether the agent may proactively offer relevant products/services.
    required_certifications:
        Certification IDs that must pass before deployment.
    """

    agent_name: str
    brand_name: str = "Customer Support"
    tone_policy: TonePolicy = "empathetic"
    model_name: str = "provider-default"
    model_provider: str = "anthropic"
    max_output_tokens: int = 1_024
    temperature: float = 0.4
    safety_rules_path: str = str(
        Path(__file__).parent / "safety" / "escalation_policy.yaml"
    )
    escalation_policy: EscalationPolicy = field(default_factory=EscalationPolicy)
    monitoring: CustomerServiceMonitoringConfig = field(
        default_factory=CustomerServiceMonitoringConfig
    )
    enable_pii_redaction: bool = True
    supported_languages: tuple[str, ...] = ("en",)
    max_session_duration_minutes: int = 60
    allow_proactive_offers: bool = False
    required_certifications: tuple[str, ...] = (
        "customer_service.pii_handling",
        "customer_service.escalation_compliance",
        "customer_service.tone_policy",
        "generic.input_validation",
        "generic.rate_limiting",
    )

    def __post_init__(self) -> None:
        """Validate field constraints after construction."""
        if not self.agent_name:
            raise ValueError(
                "CustomerServiceAgentConfig.agent_name must not be empty."
            )
        if not self.brand_name:
            raise ValueError(
                "CustomerServiceAgentConfig.brand_name must not be empty."
            )
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                f"CustomerServiceAgentConfig.temperature must be in [0.0, 2.0]; "
                f"got {self.temperature!r}."
            )
        if self.max_output_tokens < 1:
            raise ValueError(
                f"CustomerServiceAgentConfig.max_output_tokens must be >= 1; "
                f"got {self.max_output_tokens!r}."
            )
        if self.escalation_policy.max_turns_before_escalation < 1:
            raise ValueError(
                "EscalationPolicy.max_turns_before_escalation must be >= 1."
            )
        if self.max_session_duration_minutes < 1:
            raise ValueError(
                "CustomerServiceAgentConfig.max_session_duration_minutes must be >= 1."
            )

    def safety_rules_exist(self) -> bool:
        """Return True if the safety_rules_path file exists on disk."""
        return os.path.isfile(self.safety_rules_path)

    def will_escalate_on(self, trigger: EscalationTrigger) -> bool:
        """Return True if this trigger is in the escalation policy."""
        return trigger in self.escalation_policy.triggers

    def supports_language(self, language_code: str) -> bool:
        """Return True if the given BCP-47 language code is supported."""
        return language_code in self.supported_languages

    def to_dict(self) -> dict[str, object]:
        """Serialise config to a plain dict for structured logging or export."""
        return {
            "agent_name": self.agent_name,
            "brand_name": self.brand_name,
            "tone_policy": self.tone_policy,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "enable_pii_redaction": self.enable_pii_redaction,
            "supported_languages": list(self.supported_languages),
            "max_session_duration_minutes": self.max_session_duration_minutes,
            "allow_proactive_offers": self.allow_proactive_offers,
            "required_certifications": list(self.required_certifications),
            "escalation_policy": {
                "triggers": list(self.escalation_policy.triggers),
                "primary_channel": self.escalation_policy.primary_channel,
                "fallback_channel": self.escalation_policy.fallback_channel,
                "max_turns_before_escalation": (
                    self.escalation_policy.max_turns_before_escalation
                ),
                "preserve_context_on_handoff": (
                    self.escalation_policy.preserve_context_on_handoff
                ),
            },
            "monitoring": {
                "enable_sentiment_tracking": self.monitoring.enable_sentiment_tracking,
                "enable_csat_collection": self.monitoring.enable_csat_collection,
                "enable_audit_trail": self.monitoring.enable_audit_trail,
                "enable_pii_scan": self.monitoring.enable_pii_scan,
                "alert_channel": self.monitoring.alert_channel,
                "latency_slo_ms": self.monitoring.latency_slo_ms,
            },
        }


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def build_customer_service_config(
    agent_name: str,
    brand_name: str = "Customer Support",
    tone_policy: TonePolicy = "empathetic",
    model_provider: str = "anthropic",
    enable_pii_redaction: bool = True,
    supported_languages: tuple[str, ...] = ("en",),
    alert_channel: str = "slack",
) -> CustomerServiceAgentConfig:
    """Build a CustomerServiceAgentConfig with sensible production defaults.

    Parameters
    ----------
    agent_name:
        Human-readable agent name.
    brand_name:
        The brand this agent represents.
    tone_policy:
        Communication tone the agent should maintain.
    model_provider:
        Provider name passed to the provider abstraction layer.
    enable_pii_redaction:
        Enable PII redaction on all logged interactions.
    supported_languages:
        BCP-47 language codes the agent supports.
    alert_channel:
        Monitoring alert destination.

    Returns
    -------
    CustomerServiceAgentConfig
        Fully configured customer service agent config.
    """
    monitoring = CustomerServiceMonitoringConfig(
        enable_sentiment_tracking=True,
        enable_csat_collection=True,
        enable_audit_trail=True,
        enable_pii_scan=enable_pii_redaction,
        alert_on_negative_sentiment=True,
        alert_channel=alert_channel,
        latency_slo_ms=3_000,
    )
    escalation = EscalationPolicy(
        triggers=(
            "customer_request",
            "sentiment_negative",
            "unresolved_after_n_turns",
            "legal_threat",
            "safety_concern",
            "complaint_severity_high",
        ),
        primary_channel="live_chat",
        fallback_channel="email_ticket",
        max_turns_before_escalation=8,
        preserve_context_on_handoff=True,
    )
    return CustomerServiceAgentConfig(
        agent_name=agent_name,
        brand_name=brand_name,
        tone_policy=tone_policy,
        model_provider=model_provider,
        enable_pii_redaction=enable_pii_redaction,
        supported_languages=supported_languages,
        monitoring=monitoring,
        escalation_policy=escalation,
    )
