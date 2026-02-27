"""Tests for agent_vertical.integrations.aumos_templates."""
from __future__ import annotations

from typing import Any

import pytest

from agent_vertical.integrations.aumos_templates import (
    AumOSComponent,
    IntegrationBinding,
    IntegrationTemplate,
    IntegrationTemplateRegistry,
    build_integration_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> IntegrationTemplateRegistry:
    return IntegrationTemplateRegistry(include_defaults=True)


@pytest.fixture()
def governance_binding() -> IntegrationBinding:
    return IntegrationBinding(
        component=AumOSComponent.GOVERNANCE,
        binding_type="event",
        required_config_keys=frozenset({"session_id", "policy_id"}),
        default_config={"audit_enabled": True, "consent_required": True},
        description="Test governance binding.",
    )


@pytest.fixture()
def minimal_template(governance_binding: IntegrationBinding) -> IntegrationTemplate:
    return IntegrationTemplate(
        template_id="test-minimal",
        domain="test",
        bindings=(governance_binding,),
        description="A minimal test template.",
    )


# ---------------------------------------------------------------------------
# AumOSComponent
# ---------------------------------------------------------------------------


class TestAumOSComponent:
    def test_governance_value(self) -> None:
        assert AumOSComponent.GOVERNANCE.value == "aumos-cowork-governance"

    def test_all_components_have_string_values(self) -> None:
        for component in AumOSComponent:
            assert isinstance(component.value, str)
            assert len(component.value) > 0


# ---------------------------------------------------------------------------
# IntegrationBinding
# ---------------------------------------------------------------------------


class TestIntegrationBinding:
    def test_is_frozen(self, governance_binding: IntegrationBinding) -> None:
        with pytest.raises((AttributeError, TypeError)):
            governance_binding.binding_type = "rpc"  # type: ignore[misc]

    def test_validate_passes_with_required_keys(
        self, governance_binding: IntegrationBinding
    ) -> None:
        config = {"session_id": "s-1", "policy_id": "p-1", "audit_enabled": True}
        errors = governance_binding.validate(config)
        assert errors == []

    def test_validate_fails_missing_key(
        self, governance_binding: IntegrationBinding
    ) -> None:
        config = {"session_id": "s-1"}  # missing policy_id
        errors = governance_binding.validate(config)
        assert len(errors) > 0
        assert any("policy_id" in e for e in errors)

    def test_resolve_returns_defaults(
        self, governance_binding: IntegrationBinding
    ) -> None:
        resolved = governance_binding.resolve()
        assert resolved["audit_enabled"] is True
        assert resolved["consent_required"] is True

    def test_resolve_merges_overrides(
        self, governance_binding: IntegrationBinding
    ) -> None:
        resolved = governance_binding.resolve({"audit_enabled": False, "new_key": "val"})
        assert resolved["audit_enabled"] is False
        assert resolved["new_key"] == "val"

    def test_resolve_does_not_mutate_defaults(
        self, governance_binding: IntegrationBinding
    ) -> None:
        governance_binding.resolve({"audit_enabled": False})
        # Resolve again — defaults should be unchanged
        resolved2 = governance_binding.resolve()
        assert resolved2["audit_enabled"] is True

    def test_optional_flag_default_false(
        self, governance_binding: IntegrationBinding
    ) -> None:
        assert governance_binding.optional is False

    def test_optional_binding(self) -> None:
        binding = IntegrationBinding(
            component=AumOSComponent.ENERGY_BUDGET,
            binding_type="rpc",
            required_config_keys=frozenset(),
            default_config={},
            description="Optional energy budget.",
            optional=True,
        )
        assert binding.optional is True


# ---------------------------------------------------------------------------
# IntegrationTemplate
# ---------------------------------------------------------------------------


class TestIntegrationTemplate:
    def test_is_frozen(self, minimal_template: IntegrationTemplate) -> None:
        with pytest.raises((AttributeError, TypeError)):
            minimal_template.template_id = "other"  # type: ignore[misc]

    def test_components_list(
        self,
        minimal_template: IntegrationTemplate,
    ) -> None:
        assert AumOSComponent.GOVERNANCE in minimal_template.components

    def test_required_bindings_excludes_optional(self) -> None:
        required = IntegrationBinding(
            component=AumOSComponent.GOVERNANCE,
            binding_type="event",
            required_config_keys=frozenset(),
            default_config={},
            description="Required binding.",
            optional=False,
        )
        optional = IntegrationBinding(
            component=AumOSComponent.ENERGY_BUDGET,
            binding_type="rpc",
            required_config_keys=frozenset(),
            default_config={},
            description="Optional binding.",
            optional=True,
        )
        template = IntegrationTemplate(
            template_id="mixed",
            domain="test",
            bindings=(required, optional),
            description="Mixed template.",
        )
        assert len(template.required_bindings) == 1
        assert len(template.optional_bindings) == 1

    def test_validate_all_passes(
        self,
        minimal_template: IntegrationTemplate,
    ) -> None:
        resolved = {
            AumOSComponent.GOVERNANCE: {"session_id": "s-1", "policy_id": "p-1"}
        }
        errors = minimal_template.validate_all(resolved)
        assert errors[AumOSComponent.GOVERNANCE] == []

    def test_validate_all_fails_missing_keys(
        self,
        minimal_template: IntegrationTemplate,
    ) -> None:
        resolved = {AumOSComponent.GOVERNANCE: {}}
        errors = minimal_template.validate_all(resolved)
        assert len(errors[AumOSComponent.GOVERNANCE]) > 0

    def test_is_valid_true(self, minimal_template: IntegrationTemplate) -> None:
        resolved = {
            AumOSComponent.GOVERNANCE: {"session_id": "s-1", "policy_id": "p-1"}
        }
        assert minimal_template.is_valid(resolved) is True

    def test_is_valid_false(self, minimal_template: IntegrationTemplate) -> None:
        resolved = {AumOSComponent.GOVERNANCE: {}}
        assert minimal_template.is_valid(resolved) is False


# ---------------------------------------------------------------------------
# IntegrationTemplateRegistry
# ---------------------------------------------------------------------------


class TestIntegrationTemplateRegistry:
    def test_default_templates_loaded(self, registry: IntegrationTemplateRegistry) -> None:
        assert registry.template_count() >= 4

    def test_get_healthcare_template(self, registry: IntegrationTemplateRegistry) -> None:
        template = registry.get("healthcare-full")
        assert template is not None
        assert template.domain == "healthcare"

    def test_get_finance_template(self, registry: IntegrationTemplateRegistry) -> None:
        template = registry.get("finance-full")
        assert template is not None
        assert template.domain == "finance"

    def test_get_missing_returns_none(self, registry: IntegrationTemplateRegistry) -> None:
        assert registry.get("nonexistent") is None

    def test_list_template_ids_sorted(self, registry: IntegrationTemplateRegistry) -> None:
        ids = registry.list_template_ids()
        assert ids == sorted(ids)

    def test_list_by_domain_healthcare(self, registry: IntegrationTemplateRegistry) -> None:
        templates = registry.list_by_domain("healthcare")
        assert len(templates) >= 1
        assert all(t.domain == "healthcare" for t in templates)

    def test_list_by_domain_case_insensitive(self, registry: IntegrationTemplateRegistry) -> None:
        templates = registry.list_by_domain("HEALTHCARE")
        assert len(templates) >= 1

    def test_list_by_domain_no_match(self, registry: IntegrationTemplateRegistry) -> None:
        templates = registry.list_by_domain("nonexistent_domain")
        assert templates == []

    def test_register_custom_template(
        self,
        registry: IntegrationTemplateRegistry,
        minimal_template: IntegrationTemplate,
    ) -> None:
        registry.register(minimal_template)
        assert registry.get("test-minimal") is not None

    def test_register_duplicate_raises(
        self,
        registry: IntegrationTemplateRegistry,
        minimal_template: IntegrationTemplate,
    ) -> None:
        registry.register(minimal_template)
        with pytest.raises(ValueError):
            registry.register(minimal_template)

    def test_empty_registry(self) -> None:
        registry = IntegrationTemplateRegistry(include_defaults=False)
        assert registry.template_count() == 0


# ---------------------------------------------------------------------------
# build_integration_config
# ---------------------------------------------------------------------------


class TestBuildIntegrationConfig:
    def test_all_components_present(self, registry: IntegrationTemplateRegistry) -> None:
        template = registry.get("healthcare-full")
        assert template is not None
        config = build_integration_config(template)
        for binding in template.bindings:
            assert binding.component in config

    def test_defaults_applied(self, registry: IntegrationTemplateRegistry) -> None:
        template = registry.get("healthcare-full")
        assert template is not None
        config = build_integration_config(template)
        gov_config = config.get(AumOSComponent.GOVERNANCE, {})
        assert gov_config.get("audit_enabled") is True

    def test_overrides_applied(self, registry: IntegrationTemplateRegistry) -> None:
        template = registry.get("healthcare-full")
        assert template is not None
        overrides = {
            AumOSComponent.OBSERVABILITY: {"service_name": "my-healthcare-agent"}
        }
        config = build_integration_config(template, overrides)
        obs_config = config.get(AumOSComponent.OBSERVABILITY, {})
        assert obs_config["service_name"] == "my-healthcare-agent"

    def test_original_template_not_mutated(
        self, registry: IntegrationTemplateRegistry
    ) -> None:
        template = registry.get("generic-minimal")
        assert template is not None
        overrides = {AumOSComponent.GOVERNANCE: {"audit_enabled": False}}
        build_integration_config(template, overrides)
        # Build again without overrides — defaults should be intact
        config2 = build_integration_config(template)
        gov_config = config2.get(AumOSComponent.GOVERNANCE, {})
        assert gov_config.get("audit_enabled") is True

    def test_no_overrides_returns_defaults(
        self, registry: IntegrationTemplateRegistry
    ) -> None:
        template = registry.get("generic-minimal")
        assert template is not None
        config = build_integration_config(template)
        obs_config = config.get(AumOSComponent.OBSERVABILITY, {})
        assert obs_config["service_name"] == "generic-agent"
