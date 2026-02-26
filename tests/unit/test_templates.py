"""Tests for template base, registry, and domain-specific templates."""
from __future__ import annotations

import pytest

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.templates.base import (
    DomainTemplate,
    TemplateNotFoundError,
    TemplateRegistry,
    get_default_registry,
    load_all_templates,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_template(
    domain: str = "healthcare",
    name: str = "test_template",
    risk_tier: RiskTier = RiskTier.INFORMATIONAL,
) -> DomainTemplate:
    return DomainTemplate(
        domain=domain,
        name=name,
        description="A test template",
        system_prompt="You are a helpful assistant.",
        tools=("search", "summarise"),
        safety_rules=("Do not diagnose", "Always disclaim"),
        evaluation_criteria=("Has disclaimer", "Grounded claims"),
        risk_tier=risk_tier,
        required_certifications=("healthcare.phi_handling",),
    )


@pytest.fixture()
def registry() -> TemplateRegistry:
    return TemplateRegistry()


@pytest.fixture()
def populated_registry(registry: TemplateRegistry) -> TemplateRegistry:
    registry.register(_make_template("healthcare", "clinical_doc"))
    registry.register(_make_template("finance", "market_analysis"))
    registry.register(_make_template("legal", "contract_review"))
    return registry


# ---------------------------------------------------------------------------
# DomainTemplate
# ---------------------------------------------------------------------------

class TestDomainTemplate:
    def test_full_name(self) -> None:
        template = _make_template("healthcare", "clinical_doc")
        assert template.full_name() == "healthcare/clinical_doc"

    def test_full_name_finance(self) -> None:
        template = _make_template("finance", "market_analysis")
        assert template.full_name() == "finance/market_analysis"

    def test_fields_accessible(self) -> None:
        template = _make_template()
        assert template.domain == "healthcare"
        assert template.name == "test_template"
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_tools_is_tuple(self) -> None:
        template = _make_template()
        assert isinstance(template.tools, tuple)

    def test_safety_rules_is_tuple(self) -> None:
        template = _make_template()
        assert isinstance(template.safety_rules, tuple)

    def test_required_certifications_is_tuple(self) -> None:
        template = _make_template()
        assert isinstance(template.required_certifications, tuple)

    def test_frozen_dataclass(self) -> None:
        template = _make_template()
        with pytest.raises((AttributeError, TypeError)):
            template.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TemplateNotFoundError
# ---------------------------------------------------------------------------

class TestTemplateNotFoundError:
    def test_error_message_contains_name(self) -> None:
        error = TemplateNotFoundError("missing_template")
        assert "missing_template" in str(error)

    def test_error_is_key_error(self) -> None:
        with pytest.raises(KeyError):
            raise TemplateNotFoundError("test")

    def test_template_name_attribute(self) -> None:
        error = TemplateNotFoundError("my_template")
        assert error.template_name == "my_template"


# ---------------------------------------------------------------------------
# TemplateRegistry
# ---------------------------------------------------------------------------

class TestTemplateRegistryRegister:
    def test_register_adds_template(self, registry: TemplateRegistry) -> None:
        registry.register(_make_template())
        assert "test_template" in registry

    def test_register_overwrites(self, registry: TemplateRegistry) -> None:
        registry.register(_make_template(name="t1", domain="healthcare"))
        registry.register(_make_template(name="t1", domain="finance"))
        assert registry.get("t1").domain == "finance"

    def test_len_after_register(self, registry: TemplateRegistry) -> None:
        assert len(registry) == 0
        registry.register(_make_template("healthcare", "t1"))
        assert len(registry) == 1

    def test_contains_after_register(self, registry: TemplateRegistry) -> None:
        registry.register(_make_template(name="my_template"))
        assert "my_template" in registry

    def test_not_contains_unregistered(self, registry: TemplateRegistry) -> None:
        assert "nonexistent" not in registry


class TestTemplateRegistryGet:
    def test_get_existing_template(self, registry: TemplateRegistry) -> None:
        template = _make_template(name="clinical_doc")
        registry.register(template)
        result = registry.get("clinical_doc")
        assert result.name == "clinical_doc"

    def test_get_missing_raises_template_not_found(
        self, registry: TemplateRegistry
    ) -> None:
        with pytest.raises(TemplateNotFoundError):
            registry.get("nonexistent")

    def test_get_missing_is_key_error(self, registry: TemplateRegistry) -> None:
        with pytest.raises(KeyError):
            registry.get("nonexistent")


class TestTemplateRegistryListTemplates:
    def test_list_all_templates(self, populated_registry: TemplateRegistry) -> None:
        templates = populated_registry.list_templates()
        assert len(templates) == 3

    def test_list_filtered_by_domain(self, populated_registry: TemplateRegistry) -> None:
        templates = populated_registry.list_templates(domain="healthcare")
        assert len(templates) == 1
        assert templates[0].domain == "healthcare"

    def test_list_sorted_by_full_name(self, populated_registry: TemplateRegistry) -> None:
        templates = populated_registry.list_templates()
        names = [t.full_name() for t in templates]
        assert names == sorted(names)

    def test_list_unknown_domain_empty(
        self, populated_registry: TemplateRegistry
    ) -> None:
        templates = populated_registry.list_templates(domain="unknown_domain")
        assert templates == []

    def test_list_no_filter_returns_all(
        self, populated_registry: TemplateRegistry
    ) -> None:
        templates = populated_registry.list_templates()
        assert len(templates) == 3


class TestTemplateRegistryListDomains:
    def test_list_domains_returns_sorted_unique(
        self, populated_registry: TemplateRegistry
    ) -> None:
        domains = populated_registry.list_domains()
        assert domains == sorted(set(domains))

    def test_list_domains_empty_registry(self, registry: TemplateRegistry) -> None:
        domains = registry.list_domains()
        assert domains == []

    def test_list_domains_contains_all_registered(
        self, populated_registry: TemplateRegistry
    ) -> None:
        domains = populated_registry.list_domains()
        assert "healthcare" in domains
        assert "finance" in domains
        assert "legal" in domains


class TestTemplateRegistryMagicMethods:
    def test_len_empty(self, registry: TemplateRegistry) -> None:
        assert len(registry) == 0

    def test_len_populated(self, populated_registry: TemplateRegistry) -> None:
        assert len(populated_registry) == 3

    def test_repr_contains_registry_name(self, registry: TemplateRegistry) -> None:
        registry.register(_make_template(name="t1"))
        assert "TemplateRegistry" in repr(registry)

    def test_repr_contains_template_names(self, registry: TemplateRegistry) -> None:
        registry.register(_make_template(name="t1"))
        assert "t1" in repr(registry)


# ---------------------------------------------------------------------------
# load_all_templates and get_default_registry
# ---------------------------------------------------------------------------

class TestLoadAllTemplates:
    def test_load_all_templates_returns_registry(self) -> None:
        registry = load_all_templates()
        assert isinstance(registry, TemplateRegistry)

    def test_load_all_templates_has_healthcare(self) -> None:
        registry = load_all_templates()
        healthcare_templates = registry.list_templates(domain="healthcare")
        assert len(healthcare_templates) > 0

    def test_load_all_templates_has_finance(self) -> None:
        registry = load_all_templates()
        finance_templates = registry.list_templates(domain="finance")
        assert len(finance_templates) > 0

    def test_load_all_templates_has_legal(self) -> None:
        registry = load_all_templates()
        legal_templates = registry.list_templates(domain="legal")
        assert len(legal_templates) > 0

    def test_load_all_templates_has_education(self) -> None:
        registry = load_all_templates()
        education_templates = registry.list_templates(domain="education")
        assert len(education_templates) > 0

    def test_get_default_registry_same_as_load(self) -> None:
        load_all_templates()
        registry = get_default_registry()
        assert isinstance(registry, TemplateRegistry)
        assert len(registry) > 0
