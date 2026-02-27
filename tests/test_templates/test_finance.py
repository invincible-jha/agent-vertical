"""Tests for the finance domain agent template (E18.1)."""
from __future__ import annotations

import pytest

from agent_vertical.templates.finance.agent import (
    FinanceAgentConfig,
    FinanceEscalationPolicy,
    FinanceMonitoringConfig,
    build_finance_config,
)


# ---------------------------------------------------------------------------
# FinanceMonitoringConfig
# ---------------------------------------------------------------------------

class TestFinanceMonitoringConfig:
    def test_default_audit_trail_enabled(self) -> None:
        config = FinanceMonitoringConfig()
        assert config.enable_audit_trail is True

    def test_default_pii_scan_enabled(self) -> None:
        config = FinanceMonitoringConfig()
        assert config.enable_pii_scan is True

    def test_default_fair_lending_monitor_enabled(self) -> None:
        config = FinanceMonitoringConfig()
        assert config.enable_fair_lending_monitor is True

    def test_default_track_model_decisions(self) -> None:
        config = FinanceMonitoringConfig()
        assert config.track_model_decisions is True

    def test_default_latency_slo(self) -> None:
        config = FinanceMonitoringConfig()
        assert config.latency_slo_ms == 3_000

    def test_custom_alert_channel(self) -> None:
        config = FinanceMonitoringConfig(alert_channel="teams")
        assert config.alert_channel == "teams"

    def test_frozen_dataclass(self) -> None:
        config = FinanceMonitoringConfig()
        with pytest.raises((AttributeError, TypeError)):
            config.alert_channel = "email"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FinanceEscalationPolicy
# ---------------------------------------------------------------------------

class TestFinanceEscalationPolicy:
    def test_default_primary_channel(self) -> None:
        policy = FinanceEscalationPolicy()
        assert policy.primary_channel == "human_analyst"

    def test_default_fallback_channel(self) -> None:
        policy = FinanceEscalationPolicy()
        assert policy.fallback_channel == "compliance_officer"

    def test_default_require_dual_review(self) -> None:
        policy = FinanceEscalationPolicy()
        assert policy.require_dual_review is True

    def test_escalation_triggers_not_empty(self) -> None:
        policy = FinanceEscalationPolicy()
        assert len(policy.escalation_triggers) > 0

    def test_fraud_signal_is_trigger(self) -> None:
        policy = FinanceEscalationPolicy()
        assert "potential_fraud_signal" in policy.escalation_triggers

    def test_frozen_dataclass(self) -> None:
        policy = FinanceEscalationPolicy()
        with pytest.raises((AttributeError, TypeError)):
            policy.primary_channel = "none"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FinanceAgentConfig
# ---------------------------------------------------------------------------

class TestFinanceAgentConfigConstruction:
    def test_minimal_construction(self) -> None:
        config = FinanceAgentConfig(agent_name="finance-agent")
        assert config.agent_name == "finance-agent"

    def test_default_risk_level(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.risk_level == "informational"

    def test_default_temperature_zero(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.temperature == 0.0

    def test_default_pcd_redaction_enabled(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.enable_pcd_redaction is True

    def test_default_fair_lending_checks_enabled(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.enable_fair_lending_checks is True

    def test_default_audit_retention_days(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.audit_retention_days == 2_555

    def test_pci_dss_in_compliance_frameworks(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert "PCI-DSS-v4" in config.compliance_frameworks

    def test_sox_in_compliance_frameworks(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert "SOX" in config.compliance_frameworks

    def test_required_certifications_not_empty(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert len(config.required_certifications) > 0

    def test_not_investment_advice_cert_present(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert "finance.not_investment_advice" in config.required_certifications

    def test_disclaimer_contains_investment_advice(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert "investment advice" in config.not_investment_advice_disclaimer.lower()

    def test_frozen_dataclass(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        with pytest.raises((AttributeError, TypeError)):
            config.agent_name = "other"  # type: ignore[misc]


class TestFinanceAgentConfigValidation:
    def test_empty_agent_name_raises(self) -> None:
        with pytest.raises(ValueError, match="agent_name"):
            FinanceAgentConfig(agent_name="")

    def test_negative_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="temperature"):
            FinanceAgentConfig(agent_name="agent", temperature=-0.1)

    def test_temperature_above_two_raises(self) -> None:
        with pytest.raises(ValueError, match="temperature"):
            FinanceAgentConfig(agent_name="agent", temperature=2.1)

    def test_zero_output_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_output_tokens"):
            FinanceAgentConfig(agent_name="agent", max_output_tokens=0)

    def test_short_audit_retention_raises(self) -> None:
        with pytest.raises(ValueError, match="audit_retention_days"):
            FinanceAgentConfig(agent_name="agent", audit_retention_days=100)

    def test_boundary_temperature_zero_valid(self) -> None:
        config = FinanceAgentConfig(agent_name="agent", temperature=0.0)
        assert config.temperature == 0.0


class TestFinanceAgentConfigMethods:
    def test_is_pcd_protected_all_enabled(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.is_pcd_protected() is True

    def test_is_pcd_protected_no_redaction(self) -> None:
        config = FinanceAgentConfig(
            agent_name="agent", enable_pcd_redaction=False
        )
        assert config.is_pcd_protected() is False

    def test_has_compliance_framework_pci(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.has_compliance_framework("PCI-DSS-v4") is True

    def test_has_compliance_framework_sox(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.has_compliance_framework("SOX") is True

    def test_has_compliance_framework_unknown(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.has_compliance_framework("UNKNOWN-FRAMEWORK") is False

    def test_to_dict_returns_dict(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_contains_agent_name(self) -> None:
        config = FinanceAgentConfig(agent_name="my-finance-agent")
        result = config.to_dict()
        assert result["agent_name"] == "my-finance-agent"

    def test_to_dict_contains_monitoring(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "monitoring" in result

    def test_to_dict_contains_escalation_policy(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        result = config.to_dict()
        assert "escalation_policy" in result

    def test_safety_rules_path_is_string(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert isinstance(config.safety_rules_path, str)

    def test_safety_rules_exist_on_disk(self) -> None:
        config = FinanceAgentConfig(agent_name="agent")
        assert config.safety_rules_exist() is True


# ---------------------------------------------------------------------------
# build_finance_config factory
# ---------------------------------------------------------------------------

class TestBuildFinanceConfig:
    def test_returns_finance_agent_config(self) -> None:
        config = build_finance_config(agent_name="factory-agent")
        assert isinstance(config, FinanceAgentConfig)

    def test_agent_name_set_correctly(self) -> None:
        config = build_finance_config(agent_name="my-finance-bot")
        assert config.agent_name == "my-finance-bot"

    def test_default_risk_level_informational(self) -> None:
        config = build_finance_config(agent_name="agent")
        assert config.risk_level == "informational"

    def test_decision_support_enables_dual_review(self) -> None:
        config = build_finance_config(
            agent_name="agent", risk_level="decision_support"
        )
        assert config.escalation_policy.require_dual_review is True

    def test_informational_disables_dual_review(self) -> None:
        config = build_finance_config(
            agent_name="agent", risk_level="informational"
        )
        assert config.escalation_policy.require_dual_review is False

    def test_advisory_disables_dual_review(self) -> None:
        config = build_finance_config(
            agent_name="agent", risk_level="advisory"
        )
        assert config.escalation_policy.require_dual_review is False

    def test_custom_alert_channel(self) -> None:
        config = build_finance_config(
            agent_name="agent", alert_channel="slack"
        )
        assert config.monitoring.alert_channel == "slack"

    def test_pcd_redaction_disabled(self) -> None:
        config = build_finance_config(
            agent_name="agent", enable_pcd_redaction=False
        )
        assert config.enable_pcd_redaction is False

    def test_fair_lending_disabled(self) -> None:
        config = build_finance_config(
            agent_name="agent", enable_fair_lending_checks=False
        )
        assert config.enable_fair_lending_checks is False
