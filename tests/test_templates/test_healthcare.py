"""Tests for the healthcare domain agent template (E18.1)."""
from __future__ import annotations

import pytest

from agent_vertical.templates.healthcare.agent import (
    EscalationPolicy,
    HealthcareAgentConfig,
    MonitoringConfig,
    build_healthcare_config,
)


# ---------------------------------------------------------------------------
# MonitoringConfig
# ---------------------------------------------------------------------------

class TestMonitoringConfig:
    def test_default_values(self) -> None:
        config = MonitoringConfig()
        assert config.enable_audit_trail is True
        assert config.enable_pii_scan is True
        assert config.enable_latency_alerts is True
        assert config.latency_slo_ms == 5_000
        assert config.enable_safety_rule_tracing is True
        assert config.alert_channel == "pagerduty"

    def test_custom_alert_channel(self) -> None:
        config = MonitoringConfig(alert_channel="slack")
        assert config.alert_channel == "slack"

    def test_frozen_dataclass(self) -> None:
        config = MonitoringConfig()
        with pytest.raises((AttributeError, TypeError)):
            config.alert_channel = "email"  # type: ignore[misc]

    def test_disabled_audit_trail(self) -> None:
        config = MonitoringConfig(enable_audit_trail=False)
        assert config.enable_audit_trail is False

    def test_high_latency_slo(self) -> None:
        config = MonitoringConfig(latency_slo_ms=10_000)
        assert config.latency_slo_ms == 10_000


# ---------------------------------------------------------------------------
# EscalationPolicy
# ---------------------------------------------------------------------------

class TestEscalationPolicy:
    def test_default_primary_channel(self) -> None:
        policy = EscalationPolicy()
        assert policy.primary_channel == "clinical_staff"

    def test_default_fallback_channel(self) -> None:
        policy = EscalationPolicy()
        assert policy.fallback_channel == "human_review"

    def test_emergency_keywords_not_empty(self) -> None:
        policy = EscalationPolicy()
        assert len(policy.emergency_trigger_keywords) > 0

    def test_chest_pain_in_emergency_keywords(self) -> None:
        policy = EscalationPolicy()
        assert "chest pain" in policy.emergency_trigger_keywords

    def test_require_human_confirmation_default(self) -> None:
        policy = EscalationPolicy()
        assert policy.require_human_confirmation is True

    def test_custom_max_advisory_rounds(self) -> None:
        policy = EscalationPolicy(max_advisory_rounds=5)
        assert policy.max_advisory_rounds == 5

    def test_frozen_dataclass(self) -> None:
        policy = EscalationPolicy()
        with pytest.raises((AttributeError, TypeError)):
            policy.primary_channel = "none"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HealthcareAgentConfig
# ---------------------------------------------------------------------------

class TestHealthcareAgentConfigConstruction:
    def test_minimal_construction(self) -> None:
        config = HealthcareAgentConfig(agent_name="test-agent")
        assert config.agent_name == "test-agent"

    def test_default_risk_level(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.risk_level == "informational"

    def test_default_model_provider(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.model_provider == "anthropic"

    def test_default_temperature(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.temperature == 0.1

    def test_default_phi_redaction_enabled(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.enable_phi_redaction is True

    def test_default_audit_retention_days(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.audit_retention_days == 2_555

    def test_advisory_risk_level(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent", risk_level="advisory")
        assert config.risk_level == "advisory"

    def test_decision_support_risk_level(self) -> None:
        config = HealthcareAgentConfig(
            agent_name="agent", risk_level="decision_support"
        )
        assert config.risk_level == "decision_support"

    def test_compliance_framework_is_hipaa(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert "HIPAA" in config.compliance_framework

    def test_required_certifications_not_empty(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert len(config.required_certifications) > 0

    def test_phi_handling_cert_present(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert "healthcare.phi_handling" in config.required_certifications

    def test_frozen_dataclass(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        with pytest.raises((AttributeError, TypeError)):
            config.agent_name = "other"  # type: ignore[misc]


class TestHealthcareAgentConfigValidation:
    def test_empty_agent_name_raises(self) -> None:
        with pytest.raises(ValueError, match="agent_name"):
            HealthcareAgentConfig(agent_name="")

    def test_negative_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="temperature"):
            HealthcareAgentConfig(agent_name="agent", temperature=-0.1)

    def test_temperature_above_two_raises(self) -> None:
        with pytest.raises(ValueError, match="temperature"):
            HealthcareAgentConfig(agent_name="agent", temperature=2.1)

    def test_zero_output_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_output_tokens"):
            HealthcareAgentConfig(agent_name="agent", max_output_tokens=0)

    def test_short_audit_retention_raises(self) -> None:
        with pytest.raises(ValueError, match="audit_retention_days"):
            HealthcareAgentConfig(agent_name="agent", audit_retention_days=100)

    def test_boundary_temperature_zero_valid(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent", temperature=0.0)
        assert config.temperature == 0.0

    def test_boundary_temperature_two_valid(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent", temperature=2.0)
        assert config.temperature == 2.0


class TestHealthcareAgentConfigMethods:
    def test_is_phi_protected_all_enabled(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.is_phi_protected() is True

    def test_is_phi_protected_no_redaction(self) -> None:
        config = HealthcareAgentConfig(
            agent_name="agent", enable_phi_redaction=False
        )
        assert config.is_phi_protected() is False

    def test_to_dict_returns_dict(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_agent_name(self) -> None:
        config = HealthcareAgentConfig(agent_name="my-agent")
        result = config.to_dict()
        assert result["agent_name"] == "my-agent"

    def test_to_dict_contains_monitoring(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "monitoring" in result
        assert isinstance(result["monitoring"], dict)

    def test_to_dict_contains_escalation_policy(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "escalation_policy" in result

    def test_safety_rules_path_is_string(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert isinstance(config.safety_rules_path, str)

    def test_safety_rules_exist_on_disk(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.safety_rules_exist() is True

    def test_clinical_guardrails_exist_on_disk(self) -> None:
        config = HealthcareAgentConfig(agent_name="agent")
        assert config.clinical_guardrails_exist() is True


# ---------------------------------------------------------------------------
# build_healthcare_config factory
# ---------------------------------------------------------------------------

class TestBuildHealthcareConfig:
    def test_returns_healthcare_agent_config(self) -> None:
        config = build_healthcare_config(agent_name="factory-agent")
        assert isinstance(config, HealthcareAgentConfig)

    def test_agent_name_set_correctly(self) -> None:
        config = build_healthcare_config(agent_name="my-agent")
        assert config.agent_name == "my-agent"

    def test_default_risk_level_informational(self) -> None:
        config = build_healthcare_config(agent_name="agent")
        assert config.risk_level == "informational"

    def test_advisory_risk_level(self) -> None:
        config = build_healthcare_config(agent_name="agent", risk_level="advisory")
        assert config.risk_level == "advisory"

    def test_advisory_enables_human_confirmation(self) -> None:
        config = build_healthcare_config(agent_name="agent", risk_level="advisory")
        assert config.escalation_policy.require_human_confirmation is True

    def test_informational_disables_human_confirmation(self) -> None:
        config = build_healthcare_config(
            agent_name="agent", risk_level="informational"
        )
        assert config.escalation_policy.require_human_confirmation is False

    def test_custom_alert_channel(self) -> None:
        config = build_healthcare_config(
            agent_name="agent", alert_channel="email"
        )
        assert config.monitoring.alert_channel == "email"

    def test_phi_redaction_disabled(self) -> None:
        config = build_healthcare_config(
            agent_name="agent", enable_phi_redaction=False
        )
        assert config.enable_phi_redaction is False
