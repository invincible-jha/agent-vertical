"""Cross-AumOS integration templates for vertical agents.

Provides ready-made integration binding templates that wire a vertical
domain agent to other AumOS platform components such as governance,
observability, identity, and memory layers.

Each :class:`IntegrationTemplate` declares which AumOS components it
connects, the configuration fields required for each binding, and
validation logic to catch misconfiguration before deployment.

The :class:`IntegrationTemplateRegistry` is a singleton-style store of
all available integration templates.  Calling :func:`build_integration_config`
merges a user-supplied overrides dict with a template's defaults to
produce a ready-to-deploy configuration.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# AumOS component identifiers
# ---------------------------------------------------------------------------


class AumOSComponent(str, Enum):
    """AumOS platform components that a vertical agent can integrate with."""

    GOVERNANCE = "aumos-cowork-governance"
    OBSERVABILITY = "agent-observability"
    IDENTITY = "agent-identity"
    MEMORY = "agent-memory"
    EVAL = "agent-eval"
    MESH_ROUTER = "agent-mesh-router"
    SESSION_LINKER = "agent-session-linker"
    ENERGY_BUDGET = "agent-energy-budget"
    SHIELD = "agentshield"


# ---------------------------------------------------------------------------
# Integration binding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrationBinding:
    """A single integration point between a vertical agent and one AumOS component.

    Attributes
    ----------
    component:
        The AumOS component being integrated.
    binding_type:
        Category of integration: ``"event"``, ``"rpc"``, ``"shared_store"``,
        ``"webhook"``, or ``"sidecar"``.
    required_config_keys:
        Config keys that *must* be present in the resolved binding config.
    default_config:
        Sensible defaults for this binding, merged with user overrides.
    description:
        Human-readable description of what this binding does.
    optional:
        When True, the agent can start without this binding being configured.
    """

    component: AumOSComponent
    binding_type: str
    required_config_keys: frozenset[str]
    default_config: dict[str, Any]
    description: str
    optional: bool = False

    def validate(self, config: dict[str, Any]) -> list[str]:
        """Return a list of validation error messages for *config*.

        Parameters
        ----------
        config:
            Resolved configuration dict for this binding.

        Returns
        -------
        list[str]
            Empty list when valid; one error message per missing or invalid key.
        """
        errors: list[str] = []
        for key in self.required_config_keys:
            if key not in config or config[key] is None:
                errors.append(
                    f"[{self.component.value}] Missing required config key: '{key}'"
                )
        return errors

    def resolve(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the binding config merged with *overrides*.

        Parameters
        ----------
        overrides:
            User-supplied overrides; merged on top of :attr:`default_config`.

        Returns
        -------
        dict[str, Any]
            Merged configuration dict.
        """
        merged = copy.deepcopy(self.default_config)
        if overrides:
            merged.update(overrides)
        return merged


# ---------------------------------------------------------------------------
# Integration template
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrationTemplate:
    """A named set of :class:`IntegrationBinding` objects for a vertical domain.

    Attributes
    ----------
    template_id:
        Unique identifier for this integration template.
    domain:
        The vertical domain this template is designed for.
    bindings:
        Tuple of bindings included in this template.
    description:
        Human-readable summary of what this template wires together.
    version:
        Semantic version of the template definition.
    """

    template_id: str
    domain: str
    bindings: tuple[IntegrationBinding, ...]
    description: str
    version: str = "1.0.0"

    @property
    def components(self) -> list[AumOSComponent]:
        """Return the list of AumOS components included in this template."""
        return [b.component for b in self.bindings]

    @property
    def required_bindings(self) -> list[IntegrationBinding]:
        """Return bindings that are not optional."""
        return [b for b in self.bindings if not b.optional]

    @property
    def optional_bindings(self) -> list[IntegrationBinding]:
        """Return bindings that are optional."""
        return [b for b in self.bindings if b.optional]

    def validate_all(
        self, resolved_configs: dict[AumOSComponent, dict[str, Any]]
    ) -> dict[AumOSComponent, list[str]]:
        """Validate all binding configs.

        Parameters
        ----------
        resolved_configs:
            Mapping from component to its resolved configuration dict.

        Returns
        -------
        dict[AumOSComponent, list[str]]
            Mapping from component to list of error messages (empty when valid).
        """
        result: dict[AumOSComponent, list[str]] = {}
        for binding in self.bindings:
            cfg = resolved_configs.get(binding.component, {})
            errors = binding.validate(cfg)
            result[binding.component] = errors
        return result

    def is_valid(
        self, resolved_configs: dict[AumOSComponent, dict[str, Any]]
    ) -> bool:
        """Return True when all required bindings are valid.

        Parameters
        ----------
        resolved_configs:
            Mapping from component to resolved configuration dict.

        Returns
        -------
        bool
            True when no required binding has validation errors.
        """
        errors = self.validate_all(resolved_configs)
        for binding in self.required_bindings:
            if errors.get(binding.component):
                return False
        return True


# ---------------------------------------------------------------------------
# Built-in integration templates
# ---------------------------------------------------------------------------


def _healthcare_template() -> IntegrationTemplate:
    return IntegrationTemplate(
        template_id="healthcare-full",
        domain="healthcare",
        description=(
            "Full integration template for HIPAA-grade healthcare agents. "
            "Wires governance, observability, identity, audit, and memory."
        ),
        bindings=(
            IntegrationBinding(
                component=AumOSComponent.GOVERNANCE,
                binding_type="event",
                required_config_keys=frozenset({"session_id", "policy_id", "audit_enabled"}),
                default_config={
                    "audit_enabled": True,
                    "consent_required": True,
                    "phi_masking": True,
                    "human_review_gate": True,
                },
                description="Co-work governance with PHI masking and human review gate.",
            ),
            IntegrationBinding(
                component=AumOSComponent.OBSERVABILITY,
                binding_type="sidecar",
                required_config_keys=frozenset({"endpoint", "service_name"}),
                default_config={
                    "service_name": "healthcare-agent",
                    "traces_enabled": True,
                    "metrics_enabled": True,
                    "log_level": "INFO",
                },
                description="OpenTelemetry observability sidecar.",
            ),
            IntegrationBinding(
                component=AumOSComponent.IDENTITY,
                binding_type="rpc",
                required_config_keys=frozenset({"identity_provider_url", "scope"}),
                default_config={
                    "scope": "healthcare:read healthcare:audit",
                    "token_ttl_seconds": 3600,
                    "require_mfa": True,
                },
                description="Identity verification with MFA for clinical users.",
            ),
            IntegrationBinding(
                component=AumOSComponent.MEMORY,
                binding_type="shared_store",
                required_config_keys=frozenset({"store_url", "namespace"}),
                default_config={
                    "namespace": "healthcare",
                    "encryption_at_rest": True,
                    "retention_days": 2557,  # ~7 years per HIPAA
                },
                description="Encrypted patient-session memory store (HIPAA retention).",
            ),
            IntegrationBinding(
                component=AumOSComponent.SHIELD,
                binding_type="sidecar",
                required_config_keys=frozenset({"shield_endpoint"}),
                default_config={
                    "prompt_injection_detection": True,
                    "pii_detection": True,
                    "output_filtering": True,
                },
                description="AgentShield security sidecar for prompt injection defense.",
            ),
        ),
        version="1.0.0",
    )


def _finance_template() -> IntegrationTemplate:
    return IntegrationTemplate(
        template_id="finance-full",
        domain="finance",
        description=(
            "Full integration template for SEC-compliant finance agents. "
            "Wires governance, observability, audit, eval, and energy budget."
        ),
        bindings=(
            IntegrationBinding(
                component=AumOSComponent.GOVERNANCE,
                binding_type="event",
                required_config_keys=frozenset({"session_id", "policy_id"}),
                default_config={
                    "audit_enabled": True,
                    "human_review_gate": True,
                    "pii_masking": True,
                    "disclaimer_required": True,
                },
                description="Co-work governance with audit trail and human review.",
            ),
            IntegrationBinding(
                component=AumOSComponent.OBSERVABILITY,
                binding_type="sidecar",
                required_config_keys=frozenset({"endpoint", "service_name"}),
                default_config={
                    "service_name": "finance-agent",
                    "traces_enabled": True,
                    "metrics_enabled": True,
                    "cost_tracking": True,
                },
                description="Observability with cost tracking for financial workloads.",
            ),
            IntegrationBinding(
                component=AumOSComponent.EVAL,
                binding_type="webhook",
                required_config_keys=frozenset({"eval_endpoint"}),
                default_config={
                    "eval_suite": "finance-compliance",
                    "pass_threshold": 0.85,
                    "block_on_failure": True,
                },
                description="Automated evaluation against finance compliance test suite.",
            ),
            IntegrationBinding(
                component=AumOSComponent.ENERGY_BUDGET,
                binding_type="rpc",
                required_config_keys=frozenset(set()),
                default_config={
                    "max_tokens_per_request": 4096,
                    "daily_token_budget": 1_000_000,
                    "alert_threshold_pct": 80,
                },
                description="Energy budget for cost governance on financial workloads.",
                optional=True,
            ),
        ),
        version="1.0.0",
    )


def _legal_template() -> IntegrationTemplate:
    return IntegrationTemplate(
        template_id="legal-core",
        domain="legal",
        description=(
            "Core integration template for legal research agents. "
            "Wires governance, observability, identity, and session linking."
        ),
        bindings=(
            IntegrationBinding(
                component=AumOSComponent.GOVERNANCE,
                binding_type="event",
                required_config_keys=frozenset({"session_id", "policy_id"}),
                default_config={
                    "audit_enabled": True,
                    "attorney_review_gate": True,
                    "privilege_notice_required": True,
                },
                description="Co-work governance with attorney review gate.",
            ),
            IntegrationBinding(
                component=AumOSComponent.OBSERVABILITY,
                binding_type="sidecar",
                required_config_keys=frozenset({"endpoint", "service_name"}),
                default_config={
                    "service_name": "legal-agent",
                    "traces_enabled": True,
                    "log_level": "INFO",
                },
                description="Observability sidecar for legal agent workloads.",
            ),
            IntegrationBinding(
                component=AumOSComponent.SESSION_LINKER,
                binding_type="rpc",
                required_config_keys=frozenset({"linker_endpoint"}),
                default_config={
                    "session_ttl_seconds": 7200,
                    "persist_context": True,
                },
                description="Session linker for multi-turn legal research sessions.",
            ),
        ),
        version="1.0.0",
    )


def _generic_minimal_template() -> IntegrationTemplate:
    return IntegrationTemplate(
        template_id="generic-minimal",
        domain="generic",
        description=(
            "Minimal integration template suitable for any vertical domain. "
            "Wires only observability and governance as a baseline."
        ),
        bindings=(
            IntegrationBinding(
                component=AumOSComponent.GOVERNANCE,
                binding_type="event",
                required_config_keys=frozenset({"session_id"}),
                default_config={"audit_enabled": True},
                description="Minimal governance binding (audit only).",
            ),
            IntegrationBinding(
                component=AumOSComponent.OBSERVABILITY,
                binding_type="sidecar",
                required_config_keys=frozenset({"endpoint", "service_name"}),
                default_config={
                    "service_name": "generic-agent",
                    "traces_enabled": True,
                },
                description="Minimal observability sidecar.",
            ),
        ),
        version="1.0.0",
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class IntegrationTemplateRegistry:
    """Store and lookup :class:`IntegrationTemplate` objects.

    A default set of built-in templates is pre-loaded on construction.
    Custom templates can be registered with :meth:`register`.
    """

    def __init__(self, include_defaults: bool = True) -> None:
        self._templates: dict[str, IntegrationTemplate] = {}
        if include_defaults:
            for template in [
                _healthcare_template(),
                _finance_template(),
                _legal_template(),
                _generic_minimal_template(),
            ]:
                self._templates[template.template_id] = template

    def register(self, template: IntegrationTemplate) -> None:
        """Register a new integration template.

        Parameters
        ----------
        template:
            The template to register.

        Raises
        ------
        ValueError
            When a template with the same ID is already registered.
        """
        if template.template_id in self._templates:
            raise ValueError(f"Template '{template.template_id}' already registered.")
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> IntegrationTemplate | None:
        """Return the template with *template_id*, or None.

        Parameters
        ----------
        template_id:
            Unique template identifier.

        Returns
        -------
        IntegrationTemplate | None
            The template, or None if not found.
        """
        return self._templates.get(template_id)

    def list_template_ids(self) -> list[str]:
        """Return sorted list of all registered template IDs."""
        return sorted(self._templates.keys())

    def list_by_domain(self, domain: str) -> list[IntegrationTemplate]:
        """Return all templates for *domain* (case-insensitive).

        Parameters
        ----------
        domain:
            Domain to filter by.

        Returns
        -------
        list[IntegrationTemplate]
            Matching templates, sorted by template_id.
        """
        target = domain.lower()
        return sorted(
            [t for t in self._templates.values() if t.domain.lower() == target],
            key=lambda t: t.template_id,
        )

    def template_count(self) -> int:
        """Return the number of registered templates."""
        return len(self._templates)


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


def build_integration_config(
    template: IntegrationTemplate,
    overrides: dict[AumOSComponent, dict[str, Any]] | None = None,
) -> dict[AumOSComponent, dict[str, Any]]:
    """Build a fully-resolved integration configuration for *template*.

    Each binding's default config is merged with the corresponding entry
    in *overrides* (if provided), producing a config dict ready for use
    by agent deployment tooling.

    Parameters
    ----------
    template:
        The integration template to resolve.
    overrides:
        Per-component override dicts.

    Returns
    -------
    dict[AumOSComponent, dict[str, Any]]
        Mapping from component to resolved configuration dict.
    """
    resolved: dict[AumOSComponent, dict[str, Any]] = {}
    component_overrides = overrides or {}

    for binding in template.bindings:
        binding_overrides = component_overrides.get(binding.component)
        resolved[binding.component] = binding.resolve(binding_overrides)

    return resolved


__all__ = [
    "AumOSComponent",
    "IntegrationBinding",
    "IntegrationTemplate",
    "IntegrationTemplateRegistry",
    "build_integration_config",
]
