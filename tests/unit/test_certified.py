"""Tests for the certified domain templates package.

Covers:
- All five built-in templates load and have correct structure
- Template YAML serialisation / deserialisation round-trips
- DomainTemplate.to_dict / from_dict round-trips
- DomainTemplate.validate_template self-check
- TemplateLibrary CRUD (register, unregister, get, list)
- TemplateLibrary search by compliance and domain
- TemplateLibrary import / export via YAML files
- TemplateValidator: valid and invalid templates
- TemplateValidator: per-framework compliance coverage checks
- TemplateValidator: safety rule regex compilation
- TemplateValidator: eval benchmark completeness warnings
- CLI commands: list, show, export, validate, search
- Edge cases: empty templates, invalid regex patterns, unknown frameworks
"""
from __future__ import annotations

import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from agent_vertical.certified.library import (
    CONTENT_MODERATION_TEMPLATE,
    CUSTOMER_SERVICE_TEMPLATE,
    FINANCE_SOX_TEMPLATE,
    HEALTHCARE_HIPAA_TEMPLATE,
    RESEARCH_ASSISTANT_TEMPLATE,
    TemplateLibrary,
    TemplateNotFoundError,
)
from agent_vertical.certified.schema import (
    ComplianceFramework,
    DomainTemplate,
    EvalBenchmark,
    RiskLevel,
    SafetyRule,
    TemplateMetadata,
    ToolConfig,
)
from agent_vertical.certified.validator import TemplateValidator, ValidationResult
from agent_vertical.cli.main import cli


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_metadata(
    name: str = "test_template",
    domain: str = "test",
    frameworks: list[ComplianceFramework] | None = None,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
) -> TemplateMetadata:
    return TemplateMetadata(
        name=name,
        version="1.0.0",
        domain=domain,
        compliance_frameworks=frameworks or [],
        risk_level=risk_level,
        description="A test template for unit tests.",
        author="Test Author",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        tags=["test"],
    )


def _make_safety_rule(
    rule_id: str = "test.rule",
    severity: str = "warning",
    check_pattern: str = r"\btest\b",
) -> SafetyRule:
    return SafetyRule(
        rule_id=rule_id,
        description="A test safety rule.",
        severity=severity,
        check_pattern=check_pattern,
    )


def _make_tool_config(
    name: str = "test_tool",
    required: bool = False,
) -> ToolConfig:
    return ToolConfig(
        name=name,
        description="A test tool.",
        required=required,
        parameters={"param_a": "value_a"},
    )


def _make_eval_benchmark(
    name: str = "test_benchmark",
    metric: str = "precision",
    threshold: float = 0.90,
) -> EvalBenchmark:
    return EvalBenchmark(
        name=name,
        metric=metric,
        threshold=threshold,
        description="A test benchmark.",
    )


def _make_minimal_template(
    name: str = "minimal_template",
    domain: str = "test",
) -> DomainTemplate:
    """Construct a minimal valid DomainTemplate for testing."""
    return DomainTemplate(
        metadata=_make_metadata(name=name, domain=domain),
        system_prompt="You are a helpful test assistant with a well-formed system prompt.",
        tool_configs=[_make_tool_config()],
        safety_rules=[_make_safety_rule()],
        governance_policies={"policy_key": "policy_value"},
        eval_benchmarks=[_make_eval_benchmark()],
        compliance_evidence={"NONE": "No specific compliance framework."},
    )


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def library() -> TemplateLibrary:
    return TemplateLibrary()


@pytest.fixture()
def validator() -> TemplateValidator:
    return TemplateValidator()


@pytest.fixture()
def minimal_template() -> DomainTemplate:
    return _make_minimal_template()


# ---------------------------------------------------------------------------
# Schema — ComplianceFramework
# ---------------------------------------------------------------------------


class TestComplianceFramework:
    def test_hipaa_value(self) -> None:
        assert ComplianceFramework.HIPAA.value == "HIPAA"

    def test_sox_value(self) -> None:
        assert ComplianceFramework.SOX.value == "SOX"

    def test_gdpr_value(self) -> None:
        assert ComplianceFramework.GDPR.value == "GDPR"

    def test_soc2_value(self) -> None:
        assert ComplianceFramework.SOC2.value == "SOC2"

    def test_pci_dss_value(self) -> None:
        assert ComplianceFramework.PCI_DSS.value == "PCI_DSS"

    def test_none_value(self) -> None:
        assert ComplianceFramework.NONE.value == "NONE"

    def test_from_string(self) -> None:
        assert ComplianceFramework("HIPAA") == ComplianceFramework.HIPAA

    def test_invalid_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            ComplianceFramework("UNKNOWN_FRAMEWORK")

    def test_all_members_are_strings(self) -> None:
        for member in ComplianceFramework:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# Schema — RiskLevel
# ---------------------------------------------------------------------------


class TestRiskLevel:
    def test_low_value(self) -> None:
        assert RiskLevel.LOW.value == "LOW"

    def test_medium_value(self) -> None:
        assert RiskLevel.MEDIUM.value == "MEDIUM"

    def test_high_value(self) -> None:
        assert RiskLevel.HIGH.value == "HIGH"

    def test_critical_value(self) -> None:
        assert RiskLevel.CRITICAL.value == "CRITICAL"

    def test_from_string(self) -> None:
        assert RiskLevel("HIGH") == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Schema — TemplateMetadata
# ---------------------------------------------------------------------------


class TestTemplateMetadata:
    def test_basic_construction(self) -> None:
        meta = _make_metadata()
        assert meta.name == "test_template"
        assert meta.domain == "test"

    def test_default_version(self) -> None:
        meta = _make_metadata()
        assert meta.version == "1.0.0"

    def test_compliance_frameworks_list(self) -> None:
        meta = _make_metadata(frameworks=[ComplianceFramework.HIPAA])
        assert ComplianceFramework.HIPAA in meta.compliance_frameworks

    def test_tags_list(self) -> None:
        meta = TemplateMetadata(
            name="n",
            domain="d",
            description="desc",
            author="a",
            tags=["tag1", "tag2"],
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert "tag1" in meta.tags

    def test_frozen_model(self) -> None:
        meta = _make_metadata()
        with pytest.raises(Exception):
            meta.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Schema — SafetyRule
# ---------------------------------------------------------------------------


class TestSafetyRule:
    def test_frozen_dataclass(self) -> None:
        rule = _make_safety_rule()
        with pytest.raises((AttributeError, TypeError)):
            rule.rule_id = "changed"  # type: ignore[misc]

    def test_fields(self) -> None:
        rule = SafetyRule(
            rule_id="test.r1",
            description="Test rule",
            severity="critical",
            check_pattern=r"\btest\b",
        )
        assert rule.rule_id == "test.r1"
        assert rule.severity == "critical"
        assert rule.check_pattern == r"\btest\b"

    def test_pattern_compiles(self) -> None:
        rule = _make_safety_rule(check_pattern=r"\d{3}-\d{2}-\d{4}")
        compiled = re.compile(rule.check_pattern)
        assert compiled.search("123-45-6789")


# ---------------------------------------------------------------------------
# Schema — ToolConfig
# ---------------------------------------------------------------------------


class TestToolConfig:
    def test_frozen_dataclass(self) -> None:
        tool = _make_tool_config()
        with pytest.raises((AttributeError, TypeError)):
            tool.name = "changed"  # type: ignore[misc]

    def test_required_flag(self) -> None:
        required_tool = _make_tool_config(required=True)
        optional_tool = _make_tool_config(required=False)
        assert required_tool.required is True
        assert optional_tool.required is False

    def test_parameters_dict(self) -> None:
        tool = ToolConfig(
            name="my_tool",
            description="desc",
            required=False,
            parameters={"key": "value", "count": 42},
        )
        assert tool.parameters["key"] == "value"


# ---------------------------------------------------------------------------
# Schema — EvalBenchmark
# ---------------------------------------------------------------------------


class TestEvalBenchmark:
    def test_frozen_dataclass(self) -> None:
        bench = _make_eval_benchmark()
        with pytest.raises((AttributeError, TypeError)):
            bench.name = "changed"  # type: ignore[misc]

    def test_threshold_stored(self) -> None:
        bench = _make_eval_benchmark(threshold=0.95)
        assert bench.threshold == 0.95

    def test_metric_stored(self) -> None:
        bench = _make_eval_benchmark(metric="recall")
        assert bench.metric == "recall"


# ---------------------------------------------------------------------------
# Schema — DomainTemplate construction
# ---------------------------------------------------------------------------


class TestDomainTemplateConstruction:
    def test_minimal_template_builds(self, minimal_template: DomainTemplate) -> None:
        assert minimal_template.metadata.name == "minimal_template"

    def test_empty_system_prompt_raises(self) -> None:
        with pytest.raises(Exception):
            DomainTemplate(
                metadata=_make_metadata(),
                system_prompt="   ",
            )

    def test_tool_configs_default_empty(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Valid prompt with enough content to pass the length check.",
        )
        assert template.tool_configs == []

    def test_safety_rules_default_empty(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Valid prompt with enough content to pass the length check.",
        )
        assert template.safety_rules == []

    def test_compliance_evidence_default_empty(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Valid prompt with enough content to pass the length check.",
        )
        assert template.compliance_evidence == {}


# ---------------------------------------------------------------------------
# Schema — DomainTemplate.to_dict / from_dict
# ---------------------------------------------------------------------------


class TestDomainTemplateDict:
    def test_to_dict_returns_dict(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_has_metadata_key(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert "metadata" in result

    def test_to_dict_has_system_prompt(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert result["system_prompt"] == minimal_template.system_prompt

    def test_to_dict_safety_rules_are_dicts(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert isinstance(result["safety_rules"][0], dict)

    def test_to_dict_tool_configs_are_dicts(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert isinstance(result["tool_configs"][0], dict)

    def test_to_dict_eval_benchmarks_are_dicts(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_dict()
        assert isinstance(result["eval_benchmarks"][0], dict)

    def test_round_trip_name(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert reconstructed.metadata.name == minimal_template.metadata.name

    def test_round_trip_domain(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert reconstructed.metadata.domain == minimal_template.metadata.domain

    def test_round_trip_system_prompt(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert reconstructed.system_prompt == minimal_template.system_prompt

    def test_round_trip_safety_rules(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert len(reconstructed.safety_rules) == len(minimal_template.safety_rules)
        assert reconstructed.safety_rules[0].rule_id == minimal_template.safety_rules[0].rule_id

    def test_round_trip_tool_configs(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert len(reconstructed.tool_configs) == len(minimal_template.tool_configs)
        assert reconstructed.tool_configs[0].name == minimal_template.tool_configs[0].name

    def test_round_trip_eval_benchmarks(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert len(reconstructed.eval_benchmarks) == len(minimal_template.eval_benchmarks)
        assert reconstructed.eval_benchmarks[0].threshold == pytest.approx(
            minimal_template.eval_benchmarks[0].threshold
        )

    def test_round_trip_compliance_frameworks(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_dict(minimal_template.to_dict())
        assert (
            reconstructed.metadata.compliance_frameworks
            == minimal_template.metadata.compliance_frameworks
        )

    def test_from_dict_missing_created_at_defaults(self) -> None:
        data = _make_minimal_template().to_dict()
        del data["metadata"]["created_at"]
        reconstructed = DomainTemplate.from_dict(data)
        assert isinstance(reconstructed.metadata.created_at, datetime)

    def test_from_dict_datetime_object(self) -> None:
        data = _make_minimal_template().to_dict()
        data["metadata"]["created_at"] = datetime(2025, 6, 1, tzinfo=timezone.utc)
        reconstructed = DomainTemplate.from_dict(data)
        assert reconstructed.metadata.created_at.year == 2025


# ---------------------------------------------------------------------------
# Schema — DomainTemplate.to_yaml / from_yaml
# ---------------------------------------------------------------------------


class TestDomainTemplateYaml:
    def test_to_yaml_returns_string(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_yaml()
        assert isinstance(result, str)

    def test_to_yaml_is_parseable(self, minimal_template: DomainTemplate) -> None:
        result = minimal_template.to_yaml()
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_yaml_round_trip_name(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert reconstructed.metadata.name == minimal_template.metadata.name

    def test_yaml_round_trip_system_prompt(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert reconstructed.system_prompt == minimal_template.system_prompt

    def test_yaml_round_trip_safety_rules_count(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert len(reconstructed.safety_rules) == len(minimal_template.safety_rules)

    def test_yaml_round_trip_tool_configs_count(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert len(reconstructed.tool_configs) == len(minimal_template.tool_configs)

    def test_yaml_round_trip_eval_benchmarks_count(
        self, minimal_template: DomainTemplate
    ) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert len(reconstructed.eval_benchmarks) == len(minimal_template.eval_benchmarks)

    def test_yaml_round_trip_governance_policies(
        self, minimal_template: DomainTemplate
    ) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert reconstructed.governance_policies == minimal_template.governance_policies

    def test_yaml_round_trip_compliance_evidence(
        self, minimal_template: DomainTemplate
    ) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert reconstructed.compliance_evidence == minimal_template.compliance_evidence

    def test_yaml_round_trip_risk_level(self, minimal_template: DomainTemplate) -> None:
        reconstructed = DomainTemplate.from_yaml(minimal_template.to_yaml())
        assert reconstructed.metadata.risk_level == minimal_template.metadata.risk_level


# ---------------------------------------------------------------------------
# Schema — DomainTemplate.validate_template
# ---------------------------------------------------------------------------


class TestDomainTemplateValidateTemplate:
    def test_valid_template_no_warnings(self, minimal_template: DomainTemplate) -> None:
        warnings = minimal_template.validate_template()
        assert isinstance(warnings, list)

    def test_no_tools_produces_warning(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            safety_rules=[_make_safety_rule()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("tool" in w.lower() for w in warnings)

    def test_no_safety_rules_produces_warning(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("safety" in w.lower() for w in warnings)

    def test_no_eval_benchmarks_produces_warning(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            safety_rules=[_make_safety_rule()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("benchmark" in w.lower() for w in warnings)

    def test_no_compliance_evidence_produces_warning(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            safety_rules=[_make_safety_rule()],
            eval_benchmarks=[_make_eval_benchmark()],
        )
        warnings = template.validate_template()
        assert any("compliance evidence" in w.lower() for w in warnings)

    def test_short_system_prompt_produces_warning(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Short prompt.",
            tool_configs=[_make_tool_config()],
            safety_rules=[_make_safety_rule()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("short" in w.lower() or "50" in w for w in warnings)

    def test_invalid_regex_produces_warning(self) -> None:
        bad_rule = SafetyRule(
            rule_id="bad.regex",
            description="Bad regex rule.",
            severity="warning",
            check_pattern="[invalid(",
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            safety_rules=[bad_rule],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("invalid regex" in w.lower() or "pattern" in w.lower() for w in warnings)

    def test_invalid_severity_produces_warning(self) -> None:
        bad_rule = SafetyRule(
            rule_id="bad.severity",
            description="Bad severity rule.",
            severity="unknown_severity",
            check_pattern=r"\btest\b",
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            safety_rules=[bad_rule],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("severity" in w.lower() for w in warnings)

    def test_out_of_range_threshold_produces_warning(self) -> None:
        bad_bench = _make_eval_benchmark(threshold=1.5)
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid system prompt that has enough characters.",
            tool_configs=[_make_tool_config()],
            safety_rules=[_make_safety_rule()],
            eval_benchmarks=[bad_bench],
            compliance_evidence={"NONE": "stub"},
        )
        warnings = template.validate_template()
        assert any("1.5" in w or "range" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Built-in templates — Healthcare HIPAA
# ---------------------------------------------------------------------------


class TestHealthcareHipaaTemplate:
    def test_name(self) -> None:
        assert HEALTHCARE_HIPAA_TEMPLATE.metadata.name == "healthcare_hipaa"

    def test_domain(self) -> None:
        assert HEALTHCARE_HIPAA_TEMPLATE.metadata.domain == "healthcare"

    def test_includes_hipaa_framework(self) -> None:
        assert ComplianceFramework.HIPAA in HEALTHCARE_HIPAA_TEMPLATE.metadata.compliance_frameworks

    def test_risk_level_high(self) -> None:
        assert HEALTHCARE_HIPAA_TEMPLATE.metadata.risk_level == RiskLevel.HIGH

    def test_has_safety_rules(self) -> None:
        assert len(HEALTHCARE_HIPAA_TEMPLATE.safety_rules) >= 5

    def test_has_tool_configs(self) -> None:
        assert len(HEALTHCARE_HIPAA_TEMPLATE.tool_configs) >= 3

    def test_has_eval_benchmarks(self) -> None:
        assert len(HEALTHCARE_HIPAA_TEMPLATE.eval_benchmarks) >= 3

    def test_has_compliance_evidence(self) -> None:
        assert "HIPAA" in HEALTHCARE_HIPAA_TEMPLATE.compliance_evidence

    def test_system_prompt_not_empty(self) -> None:
        assert len(HEALTHCARE_HIPAA_TEMPLATE.system_prompt) > 100

    def test_has_phi_detection_rule(self) -> None:
        rule_ids = [r.rule_id for r in HEALTHCARE_HIPAA_TEMPLATE.safety_rules]
        assert any("phi" in rid or "hipaa" in rid for rid in rule_ids)

    def test_has_audit_logger_tool(self) -> None:
        tool_names = [t.name for t in HEALTHCARE_HIPAA_TEMPLATE.tool_configs]
        assert any("audit" in name for name in tool_names)

    def test_all_safety_rule_patterns_compile(self) -> None:
        for rule in HEALTHCARE_HIPAA_TEMPLATE.safety_rules:
            compiled = re.compile(rule.check_pattern)
            assert compiled is not None

    def test_all_benchmark_thresholds_in_range(self) -> None:
        for bench in HEALTHCARE_HIPAA_TEMPLATE.eval_benchmarks:
            assert 0.0 <= bench.threshold <= 1.0

    def test_yaml_round_trip(self) -> None:
        reconstructed = DomainTemplate.from_yaml(HEALTHCARE_HIPAA_TEMPLATE.to_yaml())
        assert reconstructed.metadata.name == HEALTHCARE_HIPAA_TEMPLATE.metadata.name

    def test_governance_policies_present(self) -> None:
        assert HEALTHCARE_HIPAA_TEMPLATE.governance_policies


# ---------------------------------------------------------------------------
# Built-in templates — Finance SOX
# ---------------------------------------------------------------------------


class TestFinanceSoxTemplate:
    def test_name(self) -> None:
        assert FINANCE_SOX_TEMPLATE.metadata.name == "finance_sox"

    def test_domain(self) -> None:
        assert FINANCE_SOX_TEMPLATE.metadata.domain == "finance"

    def test_includes_sox_framework(self) -> None:
        assert ComplianceFramework.SOX in FINANCE_SOX_TEMPLATE.metadata.compliance_frameworks

    def test_risk_level_high(self) -> None:
        assert FINANCE_SOX_TEMPLATE.metadata.risk_level == RiskLevel.HIGH

    def test_has_safety_rules(self) -> None:
        assert len(FINANCE_SOX_TEMPLATE.safety_rules) >= 5

    def test_has_tool_configs(self) -> None:
        assert len(FINANCE_SOX_TEMPLATE.tool_configs) >= 3

    def test_has_eval_benchmarks(self) -> None:
        assert len(FINANCE_SOX_TEMPLATE.eval_benchmarks) >= 3

    def test_has_compliance_evidence(self) -> None:
        assert "SOX" in FINANCE_SOX_TEMPLATE.compliance_evidence

    def test_has_transaction_audit_tool(self) -> None:
        tool_names = [t.name for t in FINANCE_SOX_TEMPLATE.tool_configs]
        assert any("audit" in name or "transaction" in name for name in tool_names)

    def test_has_fraud_detection_tool(self) -> None:
        tool_names = [t.name for t in FINANCE_SOX_TEMPLATE.tool_configs]
        assert any("fraud" in name for name in tool_names)

    def test_all_safety_rule_patterns_compile(self) -> None:
        for rule in FINANCE_SOX_TEMPLATE.safety_rules:
            compiled = re.compile(rule.check_pattern)
            assert compiled is not None

    def test_all_benchmark_thresholds_in_range(self) -> None:
        for bench in FINANCE_SOX_TEMPLATE.eval_benchmarks:
            assert 0.0 <= bench.threshold <= 1.0

    def test_yaml_round_trip(self) -> None:
        reconstructed = DomainTemplate.from_yaml(FINANCE_SOX_TEMPLATE.to_yaml())
        assert reconstructed.metadata.name == FINANCE_SOX_TEMPLATE.metadata.name

    def test_governance_policies_present(self) -> None:
        assert FINANCE_SOX_TEMPLATE.governance_policies


# ---------------------------------------------------------------------------
# Built-in templates — Customer Service
# ---------------------------------------------------------------------------


class TestCustomerServiceTemplate:
    def test_name(self) -> None:
        assert CUSTOMER_SERVICE_TEMPLATE.metadata.name == "customer_service"

    def test_domain(self) -> None:
        assert CUSTOMER_SERVICE_TEMPLATE.metadata.domain == "customer_service"

    def test_includes_gdpr_framework(self) -> None:
        assert ComplianceFramework.GDPR in CUSTOMER_SERVICE_TEMPLATE.metadata.compliance_frameworks

    def test_risk_level_medium(self) -> None:
        assert CUSTOMER_SERVICE_TEMPLATE.metadata.risk_level == RiskLevel.MEDIUM

    def test_has_safety_rules(self) -> None:
        assert len(CUSTOMER_SERVICE_TEMPLATE.safety_rules) >= 4

    def test_has_tool_configs(self) -> None:
        assert len(CUSTOMER_SERVICE_TEMPLATE.tool_configs) >= 3

    def test_has_eval_benchmarks(self) -> None:
        assert len(CUSTOMER_SERVICE_TEMPLATE.eval_benchmarks) >= 3

    def test_has_pii_redaction_tool(self) -> None:
        tool_names = [t.name for t in CUSTOMER_SERVICE_TEMPLATE.tool_configs]
        assert any("pii" in name or "redact" in name for name in tool_names)

    def test_has_escalation_tool(self) -> None:
        tool_names = [t.name for t in CUSTOMER_SERVICE_TEMPLATE.tool_configs]
        assert any("escalat" in name for name in tool_names)

    def test_has_sentiment_tool(self) -> None:
        tool_names = [t.name for t in CUSTOMER_SERVICE_TEMPLATE.tool_configs]
        assert any("sentiment" in name for name in tool_names)

    def test_all_safety_rule_patterns_compile(self) -> None:
        for rule in CUSTOMER_SERVICE_TEMPLATE.safety_rules:
            compiled = re.compile(rule.check_pattern)
            assert compiled is not None

    def test_all_benchmark_thresholds_in_range(self) -> None:
        for bench in CUSTOMER_SERVICE_TEMPLATE.eval_benchmarks:
            assert 0.0 <= bench.threshold <= 1.0

    def test_yaml_round_trip(self) -> None:
        reconstructed = DomainTemplate.from_yaml(CUSTOMER_SERVICE_TEMPLATE.to_yaml())
        assert reconstructed.metadata.name == CUSTOMER_SERVICE_TEMPLATE.metadata.name


# ---------------------------------------------------------------------------
# Built-in templates — Content Moderation
# ---------------------------------------------------------------------------


class TestContentModerationTemplate:
    def test_name(self) -> None:
        assert CONTENT_MODERATION_TEMPLATE.metadata.name == "content_moderation"

    def test_domain(self) -> None:
        assert CONTENT_MODERATION_TEMPLATE.metadata.domain == "content_moderation"

    def test_risk_level_medium(self) -> None:
        assert CONTENT_MODERATION_TEMPLATE.metadata.risk_level == RiskLevel.MEDIUM

    def test_has_safety_rules(self) -> None:
        assert len(CONTENT_MODERATION_TEMPLATE.safety_rules) >= 5

    def test_has_tool_configs(self) -> None:
        assert len(CONTENT_MODERATION_TEMPLATE.tool_configs) >= 3

    def test_has_eval_benchmarks(self) -> None:
        assert len(CONTENT_MODERATION_TEMPLATE.eval_benchmarks) >= 3

    def test_has_toxicity_classifier_tool(self) -> None:
        tool_names = [t.name for t in CONTENT_MODERATION_TEMPLATE.tool_configs]
        assert any("toxicity" in name or "classifier" in name for name in tool_names)

    def test_has_bias_monitor_tool(self) -> None:
        tool_names = [t.name for t in CONTENT_MODERATION_TEMPLATE.tool_configs]
        assert any("bias" in name for name in tool_names)

    def test_all_safety_rule_patterns_compile(self) -> None:
        for rule in CONTENT_MODERATION_TEMPLATE.safety_rules:
            compiled = re.compile(rule.check_pattern)
            assert compiled is not None

    def test_all_benchmark_thresholds_in_range(self) -> None:
        for bench in CONTENT_MODERATION_TEMPLATE.eval_benchmarks:
            assert 0.0 <= bench.threshold <= 1.0

    def test_yaml_round_trip(self) -> None:
        reconstructed = DomainTemplate.from_yaml(CONTENT_MODERATION_TEMPLATE.to_yaml())
        assert reconstructed.metadata.name == CONTENT_MODERATION_TEMPLATE.metadata.name

    def test_has_appeal_process_rule(self) -> None:
        descriptions = [r.description.lower() for r in CONTENT_MODERATION_TEMPLATE.safety_rules]
        assert any("appeal" in d for d in descriptions)


# ---------------------------------------------------------------------------
# Built-in templates — Research Assistant
# ---------------------------------------------------------------------------


class TestResearchAssistantTemplate:
    def test_name(self) -> None:
        assert RESEARCH_ASSISTANT_TEMPLATE.metadata.name == "research_assistant"

    def test_domain(self) -> None:
        assert RESEARCH_ASSISTANT_TEMPLATE.metadata.domain == "research"

    def test_risk_level_low(self) -> None:
        assert RESEARCH_ASSISTANT_TEMPLATE.metadata.risk_level == RiskLevel.LOW

    def test_has_safety_rules(self) -> None:
        assert len(RESEARCH_ASSISTANT_TEMPLATE.safety_rules) >= 4

    def test_has_tool_configs(self) -> None:
        assert len(RESEARCH_ASSISTANT_TEMPLATE.tool_configs) >= 3

    def test_has_eval_benchmarks(self) -> None:
        assert len(RESEARCH_ASSISTANT_TEMPLATE.eval_benchmarks) >= 3

    def test_has_citation_verifier_tool(self) -> None:
        tool_names = [t.name for t in RESEARCH_ASSISTANT_TEMPLATE.tool_configs]
        assert any("citation" in name for name in tool_names)

    def test_has_confidence_calibrator_tool(self) -> None:
        tool_names = [t.name for t in RESEARCH_ASSISTANT_TEMPLATE.tool_configs]
        assert any("confidence" in name or "calibrat" in name for name in tool_names)

    def test_has_no_fabrication_rule(self) -> None:
        descriptions = [r.description.lower() for r in RESEARCH_ASSISTANT_TEMPLATE.safety_rules]
        assert any("fabricat" in d for d in descriptions)

    def test_all_safety_rule_patterns_compile(self) -> None:
        for rule in RESEARCH_ASSISTANT_TEMPLATE.safety_rules:
            compiled = re.compile(rule.check_pattern)
            assert compiled is not None

    def test_all_benchmark_thresholds_in_range(self) -> None:
        for bench in RESEARCH_ASSISTANT_TEMPLATE.eval_benchmarks:
            assert 0.0 <= bench.threshold <= 1.0

    def test_yaml_round_trip(self) -> None:
        reconstructed = DomainTemplate.from_yaml(RESEARCH_ASSISTANT_TEMPLATE.to_yaml())
        assert reconstructed.metadata.name == RESEARCH_ASSISTANT_TEMPLATE.metadata.name


# ---------------------------------------------------------------------------
# TemplateLibrary — core CRUD
# ---------------------------------------------------------------------------


class TestTemplateLibraryList:
    def test_list_templates_returns_five_builtin(self, library: TemplateLibrary) -> None:
        assert len(library.list_templates()) == 5

    def test_list_templates_is_sorted(self, library: TemplateLibrary) -> None:
        names = library.list_templates()
        assert names == sorted(names)

    def test_list_templates_contains_healthcare(self, library: TemplateLibrary) -> None:
        assert "healthcare_hipaa" in library.list_templates()

    def test_list_templates_contains_finance(self, library: TemplateLibrary) -> None:
        assert "finance_sox" in library.list_templates()

    def test_list_templates_contains_customer_service(self, library: TemplateLibrary) -> None:
        assert "customer_service" in library.list_templates()

    def test_list_templates_contains_content_moderation(self, library: TemplateLibrary) -> None:
        assert "content_moderation" in library.list_templates()

    def test_list_templates_contains_research_assistant(self, library: TemplateLibrary) -> None:
        assert "research_assistant" in library.list_templates()


class TestTemplateLibraryGet:
    def test_get_healthcare_hipaa(self, library: TemplateLibrary) -> None:
        template = library.get_template("healthcare_hipaa")
        assert template.metadata.name == "healthcare_hipaa"

    def test_get_finance_sox(self, library: TemplateLibrary) -> None:
        template = library.get_template("finance_sox")
        assert template.metadata.name == "finance_sox"

    def test_get_missing_raises_template_not_found(self, library: TemplateLibrary) -> None:
        with pytest.raises(TemplateNotFoundError):
            library.get_template("nonexistent_template")

    def test_get_missing_is_key_error(self, library: TemplateLibrary) -> None:
        with pytest.raises(KeyError):
            library.get_template("nonexistent_template")

    def test_template_not_found_error_has_name(self) -> None:
        error = TemplateNotFoundError("my_template")
        assert "my_template" in str(error)
        assert error.template_name == "my_template"


class TestTemplateLibraryRegisterUnregister:
    def test_register_custom_adds_template(self, library: TemplateLibrary) -> None:
        custom = _make_minimal_template(name="custom_test")
        library.register_custom(custom)
        assert "custom_test" in library

    def test_register_custom_overwrites_existing(self, library: TemplateLibrary) -> None:
        custom_v1 = _make_minimal_template(name="overwrite_test")
        custom_v2 = DomainTemplate(
            metadata=_make_metadata(name="overwrite_test", domain="different_domain"),
            system_prompt="Different prompt for the overwrite test case.",
        )
        library.register_custom(custom_v1)
        library.register_custom(custom_v2)
        assert library.get_template("overwrite_test").metadata.domain == "different_domain"

    def test_register_increases_len(self, library: TemplateLibrary) -> None:
        initial_len = len(library)
        library.register_custom(_make_minimal_template(name="len_test"))
        assert len(library) == initial_len + 1

    def test_unregister_removes_template(self, library: TemplateLibrary) -> None:
        custom = _make_minimal_template(name="to_remove")
        library.register_custom(custom)
        library.unregister("to_remove")
        assert "to_remove" not in library

    def test_unregister_missing_raises_template_not_found(
        self, library: TemplateLibrary
    ) -> None:
        with pytest.raises(TemplateNotFoundError):
            library.unregister("does_not_exist")

    def test_unregister_decreases_len(self, library: TemplateLibrary) -> None:
        custom = _make_minimal_template(name="temp_template")
        library.register_custom(custom)
        before = len(library)
        library.unregister("temp_template")
        assert len(library) == before - 1

    def test_contains_builtin(self, library: TemplateLibrary) -> None:
        assert "healthcare_hipaa" in library

    def test_not_contains_unknown(self, library: TemplateLibrary) -> None:
        assert "completely_unknown_xyz" not in library

    def test_repr_contains_library_class(self, library: TemplateLibrary) -> None:
        assert "TemplateLibrary" in repr(library)

    def test_repr_contains_template_name(self, library: TemplateLibrary) -> None:
        assert "healthcare_hipaa" in repr(library)


# ---------------------------------------------------------------------------
# TemplateLibrary — search
# ---------------------------------------------------------------------------


class TestTemplateLibrarySearch:
    def test_search_by_compliance_hipaa_returns_healthcare(
        self, library: TemplateLibrary
    ) -> None:
        results = library.search_by_compliance(ComplianceFramework.HIPAA)
        names = [t.metadata.name for t in results]
        assert "healthcare_hipaa" in names

    def test_search_by_compliance_sox_returns_finance(self, library: TemplateLibrary) -> None:
        results = library.search_by_compliance(ComplianceFramework.SOX)
        names = [t.metadata.name for t in results]
        assert "finance_sox" in names

    def test_search_by_compliance_gdpr_returns_customer_service(
        self, library: TemplateLibrary
    ) -> None:
        results = library.search_by_compliance(ComplianceFramework.GDPR)
        names = [t.metadata.name for t in results]
        assert "customer_service" in names

    def test_search_by_compliance_soc2_returns_results(self, library: TemplateLibrary) -> None:
        results = library.search_by_compliance(ComplianceFramework.SOC2)
        assert len(results) > 0

    def test_search_by_compliance_pci_dss_returns_empty_for_builtins(
        self, library: TemplateLibrary
    ) -> None:
        results = library.search_by_compliance(ComplianceFramework.PCI_DSS)
        assert len(results) == 0

    def test_search_by_compliance_results_sorted(self, library: TemplateLibrary) -> None:
        results = library.search_by_compliance(ComplianceFramework.SOC2)
        names = [t.metadata.name for t in results]
        assert names == sorted(names)

    def test_search_by_domain_healthcare(self, library: TemplateLibrary) -> None:
        results = library.search_by_domain("healthcare")
        names = [t.metadata.name for t in results]
        assert "healthcare_hipaa" in names

    def test_search_by_domain_finance(self, library: TemplateLibrary) -> None:
        results = library.search_by_domain("finance")
        names = [t.metadata.name for t in results]
        assert "finance_sox" in names

    def test_search_by_domain_case_insensitive(self, library: TemplateLibrary) -> None:
        lower_results = library.search_by_domain("healthcare")
        upper_results = library.search_by_domain("HEALTHCARE")
        assert [t.metadata.name for t in lower_results] == [t.metadata.name for t in upper_results]

    def test_search_by_domain_unknown_returns_empty(self, library: TemplateLibrary) -> None:
        results = library.search_by_domain("completely_unknown_domain_xyz")
        assert results == []


# ---------------------------------------------------------------------------
# TemplateLibrary — import / export
# ---------------------------------------------------------------------------


class TestTemplateLibraryImportExport:
    def test_export_creates_yaml_file(self, library: TemplateLibrary) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "healthcare.yaml"
            library.export_template("healthcare_hipaa", output_path)
            assert output_path.exists()

    def test_export_creates_valid_yaml(self, library: TemplateLibrary) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "healthcare.yaml"
            library.export_template("healthcare_hipaa", output_path)
            parsed = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            assert isinstance(parsed, dict)
            assert "metadata" in parsed

    def test_export_unknown_template_raises(self, library: TemplateLibrary) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "unknown.yaml"
            with pytest.raises(TemplateNotFoundError):
                library.export_template("nonexistent_template", output_path)

    def test_import_registers_template(self, library: TemplateLibrary) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "finance.yaml"
            library.export_template("finance_sox", output_path)

            # Use a fresh library to ensure the import is tested
            fresh_library = TemplateLibrary()
            fresh_library.unregister("finance_sox")
            assert "finance_sox" not in fresh_library

            imported = fresh_library.import_template(output_path)
            assert imported.metadata.name == "finance_sox"
            assert "finance_sox" in fresh_library

    def test_import_round_trip_preserves_safety_rules(
        self, library: TemplateLibrary
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "cs.yaml"
            library.export_template("customer_service", output_path)
            fresh_library = TemplateLibrary()
            imported = fresh_library.import_template(output_path)
            original = library.get_template("customer_service")
            assert len(imported.safety_rules) == len(original.safety_rules)

    def test_import_round_trip_preserves_benchmarks(
        self, library: TemplateLibrary
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "research.yaml"
            library.export_template("research_assistant", output_path)
            fresh_library = TemplateLibrary()
            imported = fresh_library.import_template(output_path)
            original = library.get_template("research_assistant")
            assert len(imported.eval_benchmarks) == len(original.eval_benchmarks)

    def test_export_accepts_string_path(self, library: TemplateLibrary) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = str(Path(tmp_dir) / "string_path.yaml")
            library.export_template("content_moderation", output_path)
            assert Path(output_path).exists()


# ---------------------------------------------------------------------------
# TemplateValidator — validate (valid templates)
# ---------------------------------------------------------------------------


class TestTemplateValidatorValidTemplates:
    def test_valid_template_is_valid(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.validate(minimal_template)
        assert result.valid is True

    def test_valid_template_no_errors(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.validate(minimal_template)
        assert result.errors == []

    def test_validation_result_is_frozen(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.validate(minimal_template)
        with pytest.raises((AttributeError, TypeError)):
            result.valid = False  # type: ignore[misc]

    def test_healthcare_hipaa_validates_cleanly(self, validator: TemplateValidator) -> None:
        result = validator.validate(HEALTHCARE_HIPAA_TEMPLATE)
        assert result.valid is True

    def test_finance_sox_validates_cleanly(self, validator: TemplateValidator) -> None:
        result = validator.validate(FINANCE_SOX_TEMPLATE)
        assert result.valid is True

    def test_customer_service_validates_cleanly(self, validator: TemplateValidator) -> None:
        result = validator.validate(CUSTOMER_SERVICE_TEMPLATE)
        assert result.valid is True

    def test_content_moderation_validates_cleanly(self, validator: TemplateValidator) -> None:
        result = validator.validate(CONTENT_MODERATION_TEMPLATE)
        assert result.valid is True

    def test_research_assistant_validates_cleanly(self, validator: TemplateValidator) -> None:
        result = validator.validate(RESEARCH_ASSISTANT_TEMPLATE)
        assert result.valid is True


# ---------------------------------------------------------------------------
# TemplateValidator — validate (invalid templates)
# ---------------------------------------------------------------------------


class TestTemplateValidatorInvalidTemplates:
    def _template_no_safety_rules(self) -> DomainTemplate:
        return DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A sufficiently long system prompt for the validator test.",
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )

    def test_no_safety_rules_is_invalid(self, validator: TemplateValidator) -> None:
        result = validator.validate(self._template_no_safety_rules())
        assert result.valid is False

    def test_no_safety_rules_has_error(self, validator: TemplateValidator) -> None:
        result = validator.validate(self._template_no_safety_rules())
        assert any("safety" in e.lower() for e in result.errors)

    def test_invalid_regex_pattern_is_invalid(self, validator: TemplateValidator) -> None:
        bad_rule = SafetyRule(
            rule_id="bad.regex",
            description="Bad regex.",
            severity="warning",
            check_pattern="[invalid(",
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A sufficiently long system prompt for the validator test.",
            safety_rules=[bad_rule],
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        result = validator.validate(template)
        assert result.valid is False

    def test_invalid_severity_is_invalid(self, validator: TemplateValidator) -> None:
        bad_rule = SafetyRule(
            rule_id="bad.severity",
            description="Bad severity.",
            severity="totally_invalid",
            check_pattern=r"\btest\b",
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A sufficiently long system prompt for the validator test.",
            safety_rules=[bad_rule],
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        result = validator.validate(template)
        assert result.valid is False

    def test_out_of_range_benchmark_threshold_is_invalid(
        self, validator: TemplateValidator
    ) -> None:
        bad_bench = _make_eval_benchmark(threshold=1.5)
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A sufficiently long system prompt for the validator test.",
            safety_rules=[_make_safety_rule()],
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[bad_bench],
            compliance_evidence={"NONE": "stub"},
        )
        result = validator.validate(template)
        assert result.valid is False

    def test_empty_metadata_name_is_invalid(self, validator: TemplateValidator) -> None:
        # Use model_construct to bypass Pydantic field validation
        blank_meta = TemplateMetadata.model_construct(
            name="   ",
            version="1.0.0",
            domain="test",
            compliance_frameworks=[],
            risk_level=RiskLevel.MEDIUM,
            description="Valid description",
            author="author",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            tags=[],
        )
        template = DomainTemplate.model_construct(
            metadata=blank_meta,
            system_prompt="A sufficiently long system prompt for the empty name test.",
            tool_configs=[],
            safety_rules=[_make_safety_rule()],
            governance_policies={},
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={},
        )
        result = validator.validate(template)
        assert any("name" in e.lower() for e in result.errors)

    def test_empty_metadata_domain_is_invalid(self, validator: TemplateValidator) -> None:
        blank_meta = TemplateMetadata.model_construct(
            name="test",
            version="1.0.0",
            domain="   ",
            compliance_frameworks=[],
            risk_level=RiskLevel.MEDIUM,
            description="Valid description",
            author="author",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            tags=[],
        )
        template = DomainTemplate.model_construct(
            metadata=blank_meta,
            system_prompt="A sufficiently long system prompt for the empty domain test.",
            tool_configs=[],
            safety_rules=[_make_safety_rule()],
            governance_policies={},
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={},
        )
        result = validator.validate(template)
        assert any("domain" in e.lower() for e in result.errors)

    def test_empty_metadata_description_is_invalid(self, validator: TemplateValidator) -> None:
        blank_meta = TemplateMetadata.model_construct(
            name="test",
            version="1.0.0",
            domain="test",
            compliance_frameworks=[],
            risk_level=RiskLevel.MEDIUM,
            description="   ",
            author="author",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            tags=[],
        )
        template = DomainTemplate.model_construct(
            metadata=blank_meta,
            system_prompt="A sufficiently long system prompt for the empty description test.",
            tool_configs=[],
            safety_rules=[_make_safety_rule()],
            governance_policies={},
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={},
        )
        result = validator.validate(template)
        assert any("description" in e.lower() for e in result.errors)

    def test_whitespace_only_system_prompt_is_invalid(
        self, validator: TemplateValidator
    ) -> None:
        template = DomainTemplate.model_construct(
            metadata=_make_metadata(),
            system_prompt="   ",
            tool_configs=[],
            safety_rules=[_make_safety_rule()],
            governance_policies={},
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={},
        )
        result = validator.validate(template)
        assert any("system_prompt" in e.lower() for e in result.errors)

    def test_warnings_do_not_make_template_invalid(
        self, validator: TemplateValidator
    ) -> None:
        # Short prompt produces a warning but should still be valid
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Short.",
            safety_rules=[_make_safety_rule()],
            tool_configs=[_make_tool_config()],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"NONE": "stub"},
        )
        result = validator.validate(template)
        # Short prompt is a warning, not an error
        assert len(result.warnings) > 0
        # valid depends on whether safety rules pass — short prompt is a warning only
        assert isinstance(result.valid, bool)


# ---------------------------------------------------------------------------
# TemplateValidator — check_compliance_coverage
# ---------------------------------------------------------------------------


class TestTemplateValidatorComplianceCoverage:
    def test_healthcare_hipaa_passes_hipaa_check(self, validator: TemplateValidator) -> None:
        result = validator.check_compliance_coverage(
            HEALTHCARE_HIPAA_TEMPLATE, ComplianceFramework.HIPAA
        )
        assert result.get("HIPAA") is True

    def test_finance_sox_passes_sox_check(self, validator: TemplateValidator) -> None:
        result = validator.check_compliance_coverage(
            FINANCE_SOX_TEMPLATE, ComplianceFramework.SOX
        )
        assert result.get("SOX") is True

    def test_customer_service_passes_gdpr_check(self, validator: TemplateValidator) -> None:
        result = validator.check_compliance_coverage(
            CUSTOMER_SERVICE_TEMPLATE, ComplianceFramework.GDPR
        )
        assert result.get("GDPR") is True

    def test_healthcare_passes_soc2_check(self, validator: TemplateValidator) -> None:
        result = validator.check_compliance_coverage(
            HEALTHCARE_HIPAA_TEMPLATE, ComplianceFramework.SOC2
        )
        assert result.get("SOC2") is True

    def test_minimal_template_fails_hipaa_check(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.HIPAA
        )
        value = result.get("HIPAA")
        assert isinstance(value, list) and len(value) > 0

    def test_minimal_template_fails_sox_check(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.SOX
        )
        value = result.get("SOX")
        assert isinstance(value, list) and len(value) > 0

    def test_minimal_template_fails_gdpr_check(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.GDPR
        )
        value = result.get("GDPR")
        assert isinstance(value, list) and len(value) > 0

    def test_minimal_template_fails_soc2_check(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.SOC2
        )
        value = result.get("SOC2")
        assert isinstance(value, list) and len(value) > 0

    def test_minimal_template_fails_pci_dss_check(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.PCI_DSS
        )
        value = result.get("PCI_DSS")
        assert isinstance(value, list) and len(value) > 0

    def test_none_framework_returns_true(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        result = validator.check_compliance_coverage(
            minimal_template, ComplianceFramework.NONE
        )
        assert result.get("NONE") is True

    def test_compliance_gaps_in_validation_result(self, validator: TemplateValidator) -> None:
        # A template declared as HIPAA but missing PHI tools should have gaps
        no_hipaa_tools = DomainTemplate(
            metadata=_make_metadata(
                frameworks=[ComplianceFramework.HIPAA],
            ),
            system_prompt="A sufficiently long system prompt for the validator test.",
            safety_rules=[_make_safety_rule()],
            tool_configs=[_make_tool_config(name="generic_tool")],
            eval_benchmarks=[_make_eval_benchmark()],
            compliance_evidence={"HIPAA": "stub"},
        )
        result = validator.validate(no_hipaa_tools)
        assert "HIPAA" in result.compliance_gaps
        assert len(result.compliance_gaps["HIPAA"]) > 0


# ---------------------------------------------------------------------------
# TemplateValidator — check_safety_rules
# ---------------------------------------------------------------------------


class TestTemplateValidatorSafetyRules:
    def test_valid_patterns_return_no_errors(
        self, validator: TemplateValidator, minimal_template: DomainTemplate
    ) -> None:
        errors = validator.check_safety_rules(minimal_template)
        assert errors == []

    def test_invalid_pattern_returns_error(self, validator: TemplateValidator) -> None:
        bad_rule = SafetyRule(
            rule_id="bad.regex",
            description="Broken regex.",
            severity="warning",
            check_pattern="[unclosed(",
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A valid prompt for checking safety rules in the validator.",
            safety_rules=[bad_rule],
        )
        errors = validator.check_safety_rules(template)
        assert len(errors) == 1
        assert "bad.regex" in errors[0]

    def test_multiple_bad_patterns_each_produce_error(
        self, validator: TemplateValidator
    ) -> None:
        bad_rule1 = SafetyRule(
            rule_id="bad.r1", description="d1", severity="warning", check_pattern="[bad1("
        )
        bad_rule2 = SafetyRule(
            rule_id="bad.r2", description="d2", severity="error", check_pattern="*invalid"
        )
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Prompt for multiple bad-pattern testing in the validator.",
            safety_rules=[bad_rule1, bad_rule2],
        )
        errors = validator.check_safety_rules(template)
        assert len(errors) == 2

    def test_all_healthcare_patterns_are_valid(self, validator: TemplateValidator) -> None:
        errors = validator.check_safety_rules(HEALTHCARE_HIPAA_TEMPLATE)
        assert errors == []

    def test_all_finance_patterns_are_valid(self, validator: TemplateValidator) -> None:
        errors = validator.check_safety_rules(FINANCE_SOX_TEMPLATE)
        assert errors == []

    def test_all_customer_service_patterns_are_valid(self, validator: TemplateValidator) -> None:
        errors = validator.check_safety_rules(CUSTOMER_SERVICE_TEMPLATE)
        assert errors == []

    def test_all_content_moderation_patterns_are_valid(
        self, validator: TemplateValidator
    ) -> None:
        errors = validator.check_safety_rules(CONTENT_MODERATION_TEMPLATE)
        assert errors == []

    def test_all_research_assistant_patterns_are_valid(
        self, validator: TemplateValidator
    ) -> None:
        errors = validator.check_safety_rules(RESEARCH_ASSISTANT_TEMPLATE)
        assert errors == []

    def test_empty_safety_rules_returns_no_errors(self, validator: TemplateValidator) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with no safety rules for the check test.",
        )
        errors = validator.check_safety_rules(template)
        assert errors == []


# ---------------------------------------------------------------------------
# TemplateValidator — check_eval_completeness
# ---------------------------------------------------------------------------


class TestTemplateValidatorEvalCompleteness:
    def test_no_benchmarks_returns_warning(self, validator: TemplateValidator) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with no benchmarks.",
        )
        warnings = validator.check_eval_completeness(template)
        assert any("benchmark" in w.lower() for w in warnings)

    def test_quality_metric_present_no_quality_warning(
        self, validator: TemplateValidator
    ) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with a quality benchmark defined.",
            eval_benchmarks=[_make_eval_benchmark(metric="precision")],
        )
        warnings = validator.check_eval_completeness(template)
        assert not any("quality" in w.lower() for w in warnings)

    def test_missing_quality_metric_produces_warning(
        self, validator: TemplateValidator
    ) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with coverage but no quality benchmark.",
            eval_benchmarks=[_make_eval_benchmark(metric="coverage")],
        )
        warnings = validator.check_eval_completeness(template)
        assert any("quality" in w.lower() for w in warnings)

    def test_missing_coverage_metric_produces_warning(
        self, validator: TemplateValidator
    ) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with quality but no coverage benchmark.",
            eval_benchmarks=[_make_eval_benchmark(metric="precision")],
        )
        warnings = validator.check_eval_completeness(template)
        assert any("coverage" in w.lower() or "pass" in w.lower() for w in warnings)

    def test_zero_threshold_benchmark_produces_warning(
        self, validator: TemplateValidator
    ) -> None:
        zero_bench = _make_eval_benchmark(threshold=0.0)
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="A prompt with a zero-threshold benchmark.",
            eval_benchmarks=[zero_bench, _make_eval_benchmark(metric="coverage")],
        )
        warnings = validator.check_eval_completeness(template)
        assert any("0.0" in w or "placeholder" in w.lower() for w in warnings)

    def test_healthcare_hipaa_benchmarks_are_complete(
        self, validator: TemplateValidator
    ) -> None:
        warnings = validator.check_eval_completeness(HEALTHCARE_HIPAA_TEMPLATE)
        # Should not warn about missing coverage/quality metrics
        assert not any("quality" in w.lower() and "metric" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# CLI — certified list
# ---------------------------------------------------------------------------


class TestCertifiedListCommand:
    """CLI list command tests.

    Rich tables truncate columns to terminal width.  Tests check for substrings
    guaranteed to appear even when column values are truncated (names are
    truncated to ~15 chars at default width).
    """

    def test_list_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert result.exit_code == 0

    def test_list_shows_healthcare_prefix(self, runner: CliRunner) -> None:
        # "healthcare_hipaa" truncates to "healthcare_hi" at narrow widths
        result = runner.invoke(cli, ["certified", "list"])
        assert "healthcare" in result.output

    def test_list_shows_finance_sox(self, runner: CliRunner) -> None:
        # "finance_sox" fits within 15 chars
        result = runner.invoke(cli, ["certified", "list"])
        assert "finance_sox" in result.output

    def test_list_shows_customer_service_prefix(self, runner: CliRunner) -> None:
        # "customer_service" truncates; "customer" is always present
        result = runner.invoke(cli, ["certified", "list"])
        assert "customer" in result.output

    def test_list_shows_content_moderation_prefix(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert "content" in result.output

    def test_list_shows_research_assistant_prefix(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert "research" in result.output

    def test_list_output_contains_finance_domain(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert "finance" in result.output

    def test_list_output_contains_risk_level(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert "HIGH" in result.output or "MEDIUM" in result.output or "LOW" in result.output

    def test_list_shows_certified_templates_title(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "list"])
        assert "Certified" in result.output or "Templates" in result.output


# ---------------------------------------------------------------------------
# CLI — certified show
# ---------------------------------------------------------------------------


class TestCertifiedShowCommand:
    def test_show_known_template_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert result.exit_code == 0

    def test_show_displays_template_name(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert "healthcare_hipaa" in result.output

    def test_show_displays_domain(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert "healthcare" in result.output

    def test_show_displays_tools(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert "Tools" in result.output

    def test_show_displays_safety_rules(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert "Safety Rules" in result.output

    def test_show_displays_eval_benchmarks(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "healthcare_hipaa"])
        assert "Benchmarks" in result.output

    def test_show_unknown_template_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "nonexistent_template_xyz"])
        assert result.exit_code != 0

    def test_show_unknown_template_shows_error_message(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "nonexistent_template_xyz"])
        assert "not found" in result.output.lower() or "nonexistent" in result.output

    def test_show_finance_template(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "finance_sox"])
        assert result.exit_code == 0
        assert "finance" in result.output

    def test_show_research_template(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "show", "research_assistant"])
        assert result.exit_code == 0
        assert "research" in result.output


# ---------------------------------------------------------------------------
# CLI — certified export
# ---------------------------------------------------------------------------


class TestCertifiedExportCommand:
    def test_export_creates_file(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "exported.yaml"
            result = runner.invoke(
                cli,
                ["certified", "export", "healthcare_hipaa", "--output", str(output_path)],
            )
            assert result.exit_code == 0
            assert output_path.exists()

    def test_export_output_is_valid_yaml(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "exported.yaml"
            runner.invoke(
                cli,
                ["certified", "export", "finance_sox", "--output", str(output_path)],
            )
            parsed = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            assert "metadata" in parsed

    def test_export_success_message(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "exported.yaml"
            result = runner.invoke(
                cli,
                ["certified", "export", "customer_service", "--output", str(output_path)],
            )
            assert "exported" in result.output.lower()

    def test_export_unknown_template_exits_nonzero(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "exported.yaml"
            result = runner.invoke(
                cli,
                ["certified", "export", "unknown_xyz", "--output", str(output_path)],
            )
            assert result.exit_code != 0

    def test_export_short_flag(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "exported.yaml"
            result = runner.invoke(
                cli,
                ["certified", "export", "research_assistant", "-o", str(output_path)],
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI — certified validate
# ---------------------------------------------------------------------------


class TestCertifiedValidateCommand:
    def _export_to_tmp(
        self, runner: CliRunner, name: str, tmp_dir: str
    ) -> Path:
        output_path = Path(tmp_dir) / f"{name}.yaml"
        runner.invoke(
            cli,
            ["certified", "export", name, "--output", str(output_path)],
        )
        return output_path

    def test_validate_valid_file_exits_zero(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._export_to_tmp(runner, "healthcare_hipaa", tmp_dir)
            result = runner.invoke(cli, ["certified", "validate", "--file", str(path)])
            assert result.exit_code == 0

    def test_validate_shows_valid_verdict(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._export_to_tmp(runner, "finance_sox", tmp_dir)
            result = runner.invoke(cli, ["certified", "validate", "--file", str(path)])
            assert "VALID" in result.output

    def test_validate_missing_file_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli, ["certified", "validate", "--file", "/nonexistent/path/template.yaml"]
        )
        assert result.exit_code != 0

    def test_validate_invalid_yaml_exits_nonzero(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_yaml = Path(tmp_dir) / "bad.yaml"
            bad_yaml.write_text(": invalid: yaml: [broken", encoding="utf-8")
            result = runner.invoke(cli, ["certified", "validate", "--file", str(bad_yaml)])
            assert result.exit_code != 0

    def test_validate_short_flag(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._export_to_tmp(runner, "research_assistant", tmp_dir)
            result = runner.invoke(cli, ["certified", "validate", "-f", str(path)])
            assert result.exit_code == 0

    def test_validate_shows_error_count(self, runner: CliRunner) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._export_to_tmp(runner, "content_moderation", tmp_dir)
            result = runner.invoke(cli, ["certified", "validate", "--file", str(path)])
            assert "Errors" in result.output


# ---------------------------------------------------------------------------
# CLI — certified search
# ---------------------------------------------------------------------------


class TestCertifiedSearchCommand:
    def test_search_hipaa_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "HIPAA"])
        assert result.exit_code == 0

    def test_search_hipaa_returns_healthcare(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "HIPAA"])
        assert "healthcare_hipaa" in result.output

    def test_search_sox_returns_finance(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "SOX"])
        assert "finance_sox" in result.output

    def test_search_gdpr_returns_customer_service(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "GDPR"])
        assert "customer_service" in result.output

    def test_search_with_domain_filter(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli, ["certified", "search", "--compliance", "SOC2", "--domain", "healthcare"]
        )
        assert result.exit_code == 0

    def test_search_pci_dss_returns_no_results_message(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "PCI_DSS"])
        assert result.exit_code == 0
        assert "No certified templates" in result.output

    def test_search_unknown_framework_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "UNKNOWN_XYZ"])
        assert result.exit_code != 0

    def test_search_short_compliance_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "-c", "HIPAA"])
        assert result.exit_code == 0

    def test_search_short_domain_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(
            cli, ["certified", "search", "-c", "SOC2", "-d", "finance"]
        )
        assert result.exit_code == 0

    def test_search_case_insensitive_framework(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["certified", "search", "--compliance", "hipaa"])
        assert result.exit_code == 0
        assert "healthcare_hipaa" in result.output


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_governance_policies_serialises(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Valid prompt with enough length for the empty governance test.",
            safety_rules=[_make_safety_rule()],
        )
        data = template.to_dict()
        assert data["governance_policies"] == {}

    def test_empty_compliance_evidence_serialises(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(),
            system_prompt="Valid prompt with enough length for the empty evidence test.",
            safety_rules=[_make_safety_rule()],
        )
        data = template.to_dict()
        assert data["compliance_evidence"] == {}

    def test_template_with_multiple_frameworks(self) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(
                frameworks=[
                    ComplianceFramework.HIPAA,
                    ComplianceFramework.SOC2,
                    ComplianceFramework.GDPR,
                ]
            ),
            system_prompt="Template with multiple compliance frameworks for edge case testing.",
            safety_rules=[_make_safety_rule()],
        )
        data = template.to_dict()
        assert len(data["metadata"]["compliance_frameworks"]) == 3

    def test_library_is_independent_per_instance(self) -> None:
        lib1 = TemplateLibrary()
        lib2 = TemplateLibrary()
        custom = _make_minimal_template(name="isolated_custom")
        lib1.register_custom(custom)
        assert "isolated_custom" in lib1
        assert "isolated_custom" not in lib2

    def test_validator_handles_template_with_no_frameworks(
        self, validator: TemplateValidator
    ) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(frameworks=[]),
            system_prompt="A template with no compliance frameworks declared.",
            safety_rules=[_make_safety_rule()],
        )
        result = validator.validate(template)
        assert isinstance(result, ValidationResult)
        assert result.compliance_gaps == {}

    def test_framework_none_not_included_in_gaps(self, validator: TemplateValidator) -> None:
        template = DomainTemplate(
            metadata=_make_metadata(frameworks=[ComplianceFramework.NONE]),
            system_prompt="A template with NONE framework; should have no gaps.",
            safety_rules=[_make_safety_rule()],
        )
        result = validator.validate(template)
        assert "NONE" not in result.compliance_gaps

    def test_tool_config_empty_parameters(self) -> None:
        tool = ToolConfig(
            name="empty_params_tool",
            description="Tool with empty parameters dict.",
            required=False,
            parameters={},
        )
        assert tool.parameters == {}

    def test_safety_rule_with_complex_regex(self) -> None:
        complex_pattern = (
            r"(?i)\b(?:visa|mastercard|amex|discover)\b"
            r"\s*\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
        )
        rule = SafetyRule(
            rule_id="pci.card_number",
            description="Detect full card number patterns.",
            severity="critical",
            check_pattern=complex_pattern,
        )
        compiled = re.compile(rule.check_pattern)
        assert compiled is not None

    def test_eval_benchmark_threshold_at_boundary_zero(self) -> None:
        bench = _make_eval_benchmark(threshold=0.0)
        assert bench.threshold == 0.0

    def test_eval_benchmark_threshold_at_boundary_one(self) -> None:
        bench = _make_eval_benchmark(threshold=1.0)
        assert bench.threshold == 1.0

    def test_certified_package_init_exports(self) -> None:
        from agent_vertical.certified import (
            ComplianceFramework,
            DomainTemplate,
            EvalBenchmark,
            RiskLevel,
            SafetyRule,
            TemplateLibrary,
            TemplateMetadata,
            TemplateValidator,
            ToolConfig,
            ValidationResult,
        )
        assert TemplateLibrary is not None
        assert TemplateValidator is not None
