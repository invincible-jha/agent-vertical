"""Tests for the customer service domain agent template (E18.1)."""
from __future__ import annotations

import pytest

from agent_vertical.templates.customer_service.agent import (
    CustomerServiceAgentConfig,
    CustomerServiceMonitoringConfig,
    EscalationPolicy,
    build_customer_service_config,
)


# ---------------------------------------------------------------------------
# EscalationPolicy
# ---------------------------------------------------------------------------

class TestEscalationPolicy:
    def test_default_primary_channel(self) -> None:
        policy = EscalationPolicy()
        assert policy.primary_channel == "live_chat"

    def test_default_fallback_channel(self) -> None:
        policy = EscalationPolicy()
        assert policy.fallback_channel == "email_ticket"

    def test_default_triggers_not_empty(self) -> None:
        policy = EscalationPolicy()
        assert len(policy.triggers) > 0

    def test_customer_request_is_default_trigger(self) -> None:
        policy = EscalationPolicy()
        assert "customer_request" in policy.triggers

    def test_legal_threat_is_default_trigger(self) -> None:
        policy = EscalationPolicy()
        assert "legal_threat" in policy.triggers

    def test_default_max_turns(self) -> None:
        policy = EscalationPolicy()
        assert policy.max_turns_before_escalation == 8

    def test_default_preserve_context_on_handoff(self) -> None:
        policy = EscalationPolicy()
        assert policy.preserve_context_on_handoff is True

    def test_escalation_message_not_empty(self) -> None:
        policy = EscalationPolicy()
        assert len(policy.escalation_message_template) > 0

    def test_default_high_value_threshold(self) -> None:
        policy = EscalationPolicy()
        assert policy.high_value_customer_threshold_usd == 10_000.0

    def test_frozen_dataclass(self) -> None:
        policy = EscalationPolicy()
        with pytest.raises((AttributeError, TypeError)):
            policy.primary_channel = "phone"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CustomerServiceMonitoringConfig
# ---------------------------------------------------------------------------

class TestCustomerServiceMonitoringConfig:
    def test_default_sentiment_tracking_enabled(self) -> None:
        config = CustomerServiceMonitoringConfig()
        assert config.enable_sentiment_tracking is True

    def test_default_csat_collection_enabled(self) -> None:
        config = CustomerServiceMonitoringConfig()
        assert config.enable_csat_collection is True

    def test_default_audit_trail_enabled(self) -> None:
        config = CustomerServiceMonitoringConfig()
        assert config.enable_audit_trail is True

    def test_default_alert_channel(self) -> None:
        config = CustomerServiceMonitoringConfig()
        assert config.alert_channel == "slack"

    def test_default_latency_slo(self) -> None:
        config = CustomerServiceMonitoringConfig()
        assert config.latency_slo_ms == 3_000

    def test_frozen_dataclass(self) -> None:
        config = CustomerServiceMonitoringConfig()
        with pytest.raises((AttributeError, TypeError)):
            config.alert_channel = "pagerduty"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CustomerServiceAgentConfig
# ---------------------------------------------------------------------------

class TestCustomerServiceAgentConfigConstruction:
    def test_minimal_construction(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="cs-agent")
        assert config.agent_name == "cs-agent"

    def test_default_brand_name(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.brand_name == "Customer Support"

    def test_default_tone_policy(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.tone_policy == "empathetic"

    def test_default_temperature(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.temperature == 0.4

    def test_default_max_output_tokens(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.max_output_tokens == 1_024

    def test_default_pii_redaction_enabled(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.enable_pii_redaction is True

    def test_default_supported_languages(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert "en" in config.supported_languages

    def test_default_proactive_offers_disabled(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.allow_proactive_offers is False

    def test_required_certifications_not_empty(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert len(config.required_certifications) > 0

    def test_frozen_dataclass(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        with pytest.raises((AttributeError, TypeError)):
            config.agent_name = "other"  # type: ignore[misc]


class TestCustomerServiceAgentConfigValidation:
    def test_empty_agent_name_raises(self) -> None:
        with pytest.raises(ValueError, match="agent_name"):
            CustomerServiceAgentConfig(agent_name="")

    def test_empty_brand_name_raises(self) -> None:
        with pytest.raises(ValueError, match="brand_name"):
            CustomerServiceAgentConfig(agent_name="agent", brand_name="")

    def test_negative_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="temperature"):
            CustomerServiceAgentConfig(agent_name="agent", temperature=-0.1)

    def test_zero_output_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_output_tokens"):
            CustomerServiceAgentConfig(agent_name="agent", max_output_tokens=0)

    def test_zero_max_session_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="max_session_duration_minutes"):
            CustomerServiceAgentConfig(
                agent_name="agent", max_session_duration_minutes=0
            )


class TestCustomerServiceAgentConfigMethods:
    def test_will_escalate_on_customer_request(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.will_escalate_on("customer_request") is True

    def test_will_escalate_on_legal_threat(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.will_escalate_on("legal_threat") is True

    def test_supports_english_by_default(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.supports_language("en") is True

    def test_does_not_support_unknown_language(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.supports_language("zz") is False

    def test_multilingual_config(self) -> None:
        config = CustomerServiceAgentConfig(
            agent_name="agent",
            supported_languages=("en", "es", "fr"),
        )
        assert config.supports_language("es") is True
        assert config.supports_language("fr") is True

    def test_to_dict_returns_dict(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_agent_name(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="support-bot")
        result = config.to_dict()
        assert result["agent_name"] == "support-bot"

    def test_to_dict_contains_escalation_policy(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "escalation_policy" in result

    def test_to_dict_contains_monitoring(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "monitoring" in result

    def test_safety_rules_path_is_string(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert isinstance(config.safety_rules_path, str)

    def test_safety_rules_exist_on_disk(self) -> None:
        config = CustomerServiceAgentConfig(agent_name="agent")
        assert config.safety_rules_exist() is True


# ---------------------------------------------------------------------------
# build_customer_service_config factory
# ---------------------------------------------------------------------------

class TestBuildCustomerServiceConfig:
    def test_returns_correct_type(self) -> None:
        config = build_customer_service_config(agent_name="factory-agent")
        assert isinstance(config, CustomerServiceAgentConfig)

    def test_agent_name_set_correctly(self) -> None:
        config = build_customer_service_config(agent_name="my-cs-bot")
        assert config.agent_name == "my-cs-bot"

    def test_brand_name_passed_through(self) -> None:
        config = build_customer_service_config(
            agent_name="agent", brand_name="AcmeCorp"
        )
        assert config.brand_name == "AcmeCorp"

    def test_tone_policy_passed_through(self) -> None:
        config = build_customer_service_config(
            agent_name="agent", tone_policy="formal"
        )
        assert config.tone_policy == "formal"

    def test_default_preserve_context_on_handoff(self) -> None:
        config = build_customer_service_config(agent_name="agent")
        assert config.escalation_policy.preserve_context_on_handoff is True

    def test_custom_alert_channel(self) -> None:
        config = build_customer_service_config(
            agent_name="agent", alert_channel="pagerduty"
        )
        assert config.monitoring.alert_channel == "pagerduty"

    def test_multilingual_support(self) -> None:
        config = build_customer_service_config(
            agent_name="agent",
            supported_languages=("en", "de"),
        )
        assert config.supports_language("de") is True

    def test_pii_redaction_propagated_to_monitoring(self) -> None:
        config = build_customer_service_config(
            agent_name="agent", enable_pii_redaction=True
        )
        assert config.monitoring.enable_pii_scan is True
