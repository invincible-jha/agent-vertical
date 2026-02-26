"""Template base types — DomainTemplate dataclass and TemplateRegistry.

All domain-specific template modules (healthcare, finance, legal, education)
instantiate :class:`DomainTemplate` and register instances with a shared
:class:`TemplateRegistry`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent_vertical.certification.risk_tier import RiskTier


@dataclass(frozen=True)
class DomainTemplate:
    """A reusable agent template scoped to a specific domain and use case.

    Attributes
    ----------
    domain:
        The domain this template belongs to (e.g. ``"healthcare"``).
    name:
        Machine-readable identifier used for registry lookup
        (e.g. ``"clinical_documentation"``).
    description:
        Human-readable description of the agent's purpose.
    system_prompt:
        The full system prompt to be injected into the LLM context.
    tools:
        List of tool names the agent is permitted to use.
    safety_rules:
        Ordered list of safety rules the agent must follow, as plain strings.
    evaluation_criteria:
        Criteria used to assess response quality during benchmarking.
    risk_tier:
        The :class:`RiskTier` this template is designed for.
    required_certifications:
        Certification requirement IDs that must pass before deployment.
    """

    domain: str
    name: str
    description: str
    system_prompt: str
    tools: tuple[str, ...]
    safety_rules: tuple[str, ...]
    evaluation_criteria: tuple[str, ...]
    risk_tier: RiskTier
    required_certifications: tuple[str, ...]

    def full_name(self) -> str:
        """Return ``"domain/name"`` composite identifier."""
        return f"{self.domain}/{self.name}"


class TemplateNotFoundError(KeyError):
    """Raised when a requested template is not found in the registry."""

    def __init__(self, name: str) -> None:
        self.template_name = name
        super().__init__(
            f"Template {name!r} is not registered. "
            "Use TemplateRegistry.list_templates() to see available templates."
        )


class TemplateRegistry:
    """Central registry for :class:`DomainTemplate` instances.

    Templates are registered by their ``name`` field.  Use
    :meth:`register` to add templates and :meth:`get` to retrieve them.

    Example
    -------
    ::

        registry = TemplateRegistry()
        registry.register(my_template)
        template = registry.get("clinical_documentation")
    """

    def __init__(self) -> None:
        self._templates: dict[str, DomainTemplate] = {}

    def register(self, template: DomainTemplate) -> None:
        """Register a :class:`DomainTemplate`.

        Parameters
        ----------
        template:
            The template to register. Overwrites any existing template with
            the same ``name``.
        """
        self._templates[template.name] = template

    def get(self, name: str) -> DomainTemplate:
        """Return the template registered under ``name``.

        Parameters
        ----------
        name:
            The machine-readable template name.

        Returns
        -------
        DomainTemplate

        Raises
        ------
        TemplateNotFoundError
            If no template is registered under ``name``.
        """
        try:
            return self._templates[name]
        except KeyError:
            raise TemplateNotFoundError(name) from None

    def list_templates(self, domain: str | None = None) -> list[DomainTemplate]:
        """Return all registered templates, optionally filtered by domain.

        Parameters
        ----------
        domain:
            If provided, only return templates for this domain.

        Returns
        -------
        list[DomainTemplate]
            Templates sorted by ``full_name``.
        """
        templates = list(self._templates.values())
        if domain is not None:
            templates = [t for t in templates if t.domain == domain]
        return sorted(templates, key=lambda t: t.full_name())

    def list_domains(self) -> list[str]:
        """Return a sorted list of unique domain names across all templates."""
        return sorted({t.domain for t in self._templates.values()})

    def __len__(self) -> int:
        return len(self._templates)

    def __contains__(self, name: object) -> bool:
        return name in self._templates

    def __repr__(self) -> str:
        return f"TemplateRegistry(templates={sorted(self._templates)})"


# Module-level default registry — populated by domain modules at import time.
_default_registry: TemplateRegistry = TemplateRegistry()


def get_default_registry() -> TemplateRegistry:
    """Return the module-level default :class:`TemplateRegistry`.

    Domain template modules register their templates into this registry when
    they are imported.  Call :func:`load_all_templates` to ensure all
    built-in domain templates are loaded.
    """
    return _default_registry


def load_all_templates() -> TemplateRegistry:
    """Import all built-in domain modules and return the populated registry.

    This is the recommended way to initialise the default registry before
    using :func:`get_default_registry`.

    Returns
    -------
    TemplateRegistry
        The default registry with all built-in templates registered.
    """
    # Importing these modules triggers their module-level registration calls.
    import agent_vertical.templates.education  # noqa: F401
    import agent_vertical.templates.finance  # noqa: F401
    import agent_vertical.templates.healthcare  # noqa: F401
    import agent_vertical.templates.legal  # noqa: F401

    return _default_registry
