"""Tests for the 5 new domain templates: energy, agriculture, logistics,
real_estate, and manufacturing.

Validates:
- Each domain registers exactly 3 templates.
- All 10 domains are present after load_all_templates().
- Total template count is >= 30 (10 domains x 3 templates).
- Template field types and invariants match the DomainTemplate contract.
- Domain-specific safety rules and required certifications are present.
- RiskTier values are valid.
"""
from __future__ import annotations

import pytest

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.templates.base import (
    DomainTemplate,
    TemplateRegistry,
    load_all_templates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_DOMAINS: tuple[str, ...] = (
    "agriculture",
    "education",
    "energy",
    "finance",
    "healthcare",
    "legal",
    "logistics",
    "manufacturing",
    "real_estate",
    "retail",
)

_EXPECTED_TEMPLATES_PER_DOMAIN: dict[str, tuple[str, ...]] = {
    "energy": ("grid_monitor", "consumption_forecaster", "efficiency_auditor"),
    "agriculture": ("crop_advisor", "yield_predictor", "soil_analyzer"),
    "logistics": ("route_optimizer", "warehouse_planner", "shipment_tracker"),
    "real_estate": ("property_valuator", "market_analyzer", "lease_manager"),
    "manufacturing": ("quality_inspector", "production_scheduler", "supply_chain_monitor"),
}

_VALID_RISK_TIERS: frozenset[RiskTier] = frozenset(
    {RiskTier.INFORMATIONAL, RiskTier.ADVISORY, RiskTier.DECISION_SUPPORT}
)


@pytest.fixture(scope="module")
def full_registry() -> TemplateRegistry:
    """Return the fully populated default registry (loaded once per module)."""
    return load_all_templates()


# ---------------------------------------------------------------------------
# Registry-level: domain coverage and total count
# ---------------------------------------------------------------------------


class TestRegistryCoverage:
    def test_all_ten_domains_present(self, full_registry: TemplateRegistry) -> None:
        domains = set(full_registry.list_domains())
        for domain in _ALL_DOMAINS:
            assert domain in domains, f"Domain {domain!r} not found in registry"

    def test_total_template_count_at_least_thirty(
        self, full_registry: TemplateRegistry
    ) -> None:
        assert len(full_registry) >= 30, (
            f"Expected >= 30 templates, found {len(full_registry)}"
        )

    def test_each_new_domain_has_exactly_three_templates(
        self, full_registry: TemplateRegistry
    ) -> None:
        for domain, expected_names in _EXPECTED_TEMPLATES_PER_DOMAIN.items():
            templates = full_registry.list_templates(domain=domain)
            assert len(templates) == 3, (
                f"Domain {domain!r} has {len(templates)} templates, expected 3"
            )

    def test_new_domain_template_names_match(
        self, full_registry: TemplateRegistry
    ) -> None:
        for domain, expected_names in _EXPECTED_TEMPLATES_PER_DOMAIN.items():
            templates = full_registry.list_templates(domain=domain)
            registered_names = {t.name for t in templates}
            for name in expected_names:
                assert name in registered_names, (
                    f"Template {name!r} not found in domain {domain!r}"
                )

    def test_all_ten_domains_have_three_templates(
        self, full_registry: TemplateRegistry
    ) -> None:
        for domain in _ALL_DOMAINS:
            templates = full_registry.list_templates(domain=domain)
            assert len(templates) == 3, (
                f"Domain {domain!r} has {len(templates)} templates, expected 3"
            )


# ---------------------------------------------------------------------------
# DomainTemplate field invariants for all new domains
# ---------------------------------------------------------------------------


class TestNewDomainTemplateFieldInvariants:
    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_domain_field_matches_module_domain(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert template.domain == domain

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_name_field_matches_registry_key(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert template.name == name

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_description_is_non_empty_string(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.description, str)
        assert len(template.description.strip()) > 0

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_system_prompt_is_non_empty_string(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.system_prompt, str)
        assert len(template.system_prompt.strip()) > 0

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_tools_is_non_empty_tuple(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.tools, tuple)
        assert len(template.tools) >= 1

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_safety_rules_is_non_empty_tuple_of_strings(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.safety_rules, tuple)
        assert len(template.safety_rules) >= 1
        for rule in template.safety_rules:
            assert isinstance(rule, str) and len(rule.strip()) > 0

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_evaluation_criteria_is_non_empty_tuple_of_strings(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.evaluation_criteria, tuple)
        assert len(template.evaluation_criteria) >= 1
        for criterion in template.evaluation_criteria:
            assert isinstance(criterion, str) and len(criterion.strip()) > 0

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_risk_tier_is_valid(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert template.risk_tier in _VALID_RISK_TIERS

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_required_certifications_is_non_empty_tuple_of_strings(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert isinstance(template.required_certifications, tuple)
        assert len(template.required_certifications) >= 1
        for cert in template.required_certifications:
            assert isinstance(cert, str) and len(cert.strip()) > 0

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_full_name_format(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert template.full_name() == f"{domain}/{name}"

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_template_is_frozen(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        with pytest.raises((AttributeError, TypeError)):
            template.name = "mutated"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "domain,name",
        [
            (domain, name)
            for domain, names in _EXPECTED_TEMPLATES_PER_DOMAIN.items()
            for name in names
        ],
    )
    def test_generic_input_validation_cert_present(
        self, full_registry: TemplateRegistry, domain: str, name: str
    ) -> None:
        template = full_registry.get(name)
        assert "generic.input_validation" in template.required_certifications, (
            f"Template {name!r} missing 'generic.input_validation' certification"
        )


# ---------------------------------------------------------------------------
# Energy domain — specific assertions
# ---------------------------------------------------------------------------


class TestEnergyDomain:
    def test_grid_monitor_is_informational(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("grid_monitor")
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_consumption_forecaster_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("consumption_forecaster")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_efficiency_auditor_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("efficiency_auditor")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_grid_monitor_has_no_control_commands_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("grid_monitor")
        assert "energy.no_control_commands" in template.required_certifications

    def test_grid_monitor_tools_include_scada_api(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("grid_monitor")
        assert "scada_telemetry_api" in template.tools

    def test_consumption_forecaster_has_forecast_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("consumption_forecaster")
        assert "energy.forecast_uncertainty_disclosure" in template.required_certifications

    def test_efficiency_auditor_has_engineering_review_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("efficiency_auditor")
        assert "energy.engineering_review_gate" in template.required_certifications

    def test_all_energy_safety_rules_mention_grid_safety(
        self, full_registry: TemplateRegistry
    ) -> None:
        for name in ("grid_monitor", "consumption_forecaster", "efficiency_auditor"):
            template = full_registry.get(name)
            assert "energy.grid_safety" in template.required_certifications

    def test_grid_monitor_tools_include_alert_dispatcher(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("grid_monitor")
        assert "alert_dispatcher" in template.tools


# ---------------------------------------------------------------------------
# Agriculture domain — specific assertions
# ---------------------------------------------------------------------------


class TestAgricultureDomain:
    def test_crop_advisor_is_informational(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("crop_advisor")
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_yield_predictor_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("yield_predictor")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_soil_analyzer_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("soil_analyzer")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_crop_advisor_has_food_safety_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("crop_advisor")
        assert "agriculture.food_safety_compliance" in template.required_certifications

    def test_crop_advisor_has_registered_inputs_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("crop_advisor")
        assert "agriculture.registered_inputs_only" in template.required_certifications

    def test_yield_predictor_has_uncertainty_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("yield_predictor")
        assert "agriculture.forecast_uncertainty_disclosure" in template.required_certifications

    def test_soil_analyzer_has_environmental_impact_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("soil_analyzer")
        assert "agriculture.environmental_impact" in template.required_certifications

    def test_yield_predictor_tools_include_satellite_api(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("yield_predictor")
        assert "satellite_vegetation_index_api" in template.tools

    def test_soil_analyzer_tools_include_lime_calculator(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("soil_analyzer")
        assert "lime_requirement_calculator" in template.tools


# ---------------------------------------------------------------------------
# Logistics domain — specific assertions
# ---------------------------------------------------------------------------


class TestLogisticsDomain:
    def test_route_optimizer_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("route_optimizer")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_warehouse_planner_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("warehouse_planner")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_shipment_tracker_is_informational(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("shipment_tracker")
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_route_optimizer_has_hos_compliance_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("route_optimizer")
        assert "logistics.hos_compliance" in template.required_certifications

    def test_route_optimizer_has_human_review_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("route_optimizer")
        assert "logistics.human_review_gate" in template.required_certifications

    def test_warehouse_planner_has_safety_compliance_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("warehouse_planner")
        assert "logistics.safety_compliance" in template.required_certifications

    def test_shipment_tracker_has_pii_protection_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("shipment_tracker")
        assert "logistics.pii_protection" in template.required_certifications

    def test_route_optimizer_tools_include_hos_checker(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("route_optimizer")
        assert "hos_compliance_checker" in template.tools

    def test_shipment_tracker_tools_include_carrier_tracking_api(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("shipment_tracker")
        assert "carrier_tracking_api" in template.tools

    def test_all_logistics_templates_have_pii_protection(
        self, full_registry: TemplateRegistry
    ) -> None:
        for name in ("route_optimizer", "warehouse_planner", "shipment_tracker"):
            template = full_registry.get(name)
            assert "logistics.pii_protection" in template.required_certifications, (
                f"Template {name!r} missing logistics.pii_protection cert"
            )


# ---------------------------------------------------------------------------
# Real estate domain — specific assertions
# ---------------------------------------------------------------------------


class TestRealEstateDomain:
    def test_property_valuator_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("property_valuator")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_market_analyzer_is_informational(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("market_analyzer")
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_lease_manager_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("lease_manager")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_property_valuator_has_fair_housing_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("property_valuator")
        assert "real_estate.fair_housing_compliance" in template.required_certifications

    def test_property_valuator_has_appraisal_independence_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("property_valuator")
        assert "real_estate.appraisal_independence" in template.required_certifications

    def test_property_valuator_has_human_review_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("property_valuator")
        assert "real_estate.human_review_gate" in template.required_certifications

    def test_lease_manager_has_not_legal_advice_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("lease_manager")
        assert "real_estate.not_legal_advice" in template.required_certifications

    def test_lease_manager_has_audit_trail_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("lease_manager")
        assert "real_estate.audit_trail" in template.required_certifications

    def test_property_valuator_tools_include_comparable_sales(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("property_valuator")
        assert "comparable_sales_database" in template.tools

    def test_lease_manager_tools_include_clause_classifier(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("lease_manager")
        assert "clause_classifier" in template.tools

    def test_all_real_estate_templates_have_fair_housing_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        for name in ("property_valuator", "market_analyzer", "lease_manager"):
            template = full_registry.get(name)
            assert "real_estate.fair_housing_compliance" in template.required_certifications, (
                f"Template {name!r} missing real_estate.fair_housing_compliance cert"
            )


# ---------------------------------------------------------------------------
# Manufacturing domain — specific assertions
# ---------------------------------------------------------------------------


class TestManufacturingDomain:
    def test_quality_inspector_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_production_scheduler_is_advisory(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("production_scheduler")
        assert template.risk_tier == RiskTier.ADVISORY

    def test_supply_chain_monitor_is_informational(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("supply_chain_monitor")
        assert template.risk_tier == RiskTier.INFORMATIONAL

    def test_quality_inspector_has_no_unauthorized_disposition_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert "manufacturing.no_unauthorized_disposition" in template.required_certifications

    def test_quality_inspector_has_audit_trail_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert "manufacturing.audit_trail" in template.required_certifications

    def test_production_scheduler_has_safety_critical_change_control_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("production_scheduler")
        assert (
            "manufacturing.safety_critical_change_control"
            in template.required_certifications
        )

    def test_supply_chain_monitor_has_confidentiality_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("supply_chain_monitor")
        assert "manufacturing.confidentiality" in template.required_certifications

    def test_quality_inspector_tools_include_spc_engine(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert "spc_chart_engine" in template.tools

    def test_production_scheduler_tools_include_erp_api(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("production_scheduler")
        assert "erp_work_order_api" in template.tools

    def test_supply_chain_monitor_tools_include_geopolitical_risk_feed(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("supply_chain_monitor")
        assert "geopolitical_risk_feed" in template.tools

    def test_all_manufacturing_templates_have_quality_system_compliance_cert(
        self, full_registry: TemplateRegistry
    ) -> None:
        for name in ("quality_inspector", "production_scheduler", "supply_chain_monitor"):
            template = full_registry.get(name)
            assert (
                "manufacturing.quality_system_compliance"
                in template.required_certifications
            ), (
                f"Template {name!r} missing manufacturing.quality_system_compliance cert"
            )

    def test_quality_inspector_system_prompt_mentions_spc(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert "SPC" in template.system_prompt

    def test_quality_inspector_system_prompt_mentions_cpk(
        self, full_registry: TemplateRegistry
    ) -> None:
        template = full_registry.get("quality_inspector")
        assert "Cpk" in template.system_prompt


# ---------------------------------------------------------------------------
# Cross-domain advisory disclaimer coverage
# ---------------------------------------------------------------------------


class TestAdvisoryDisclaimerPresence:
    """Verify that every ADVISORY template's system prompt contains a
    human-review reminder — a proxy for the mandatory disclaimer requirement."""

    _advisory_templates: tuple[str, ...] = (
        "consumption_forecaster",
        "efficiency_auditor",
        "yield_predictor",
        "soil_analyzer",
        "route_optimizer",
        "warehouse_planner",
        "property_valuator",
        "lease_manager",
        "quality_inspector",
        "production_scheduler",
    )

    @pytest.mark.parametrize("name", _advisory_templates)
    def test_advisory_template_system_prompt_has_review_reminder(
        self, full_registry: TemplateRegistry, name: str
    ) -> None:
        template = full_registry.get(name)
        assert template.risk_tier == RiskTier.ADVISORY
        prompt_lower = template.system_prompt.lower()
        has_review = (
            "review" in prompt_lower
            or "approved" in prompt_lower
            or "approval" in prompt_lower
            or "consult" in prompt_lower
        )
        assert has_review, (
            f"Template {name!r} system prompt does not mention review/approval/consult"
        )
