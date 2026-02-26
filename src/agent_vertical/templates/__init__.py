"""Templates subsystem — domain-specific agent templates.

Import this package to access the built-in domain templates and the shared
:class:`TemplateRegistry`.  Call :func:`load_all_templates` to populate the
default registry with all built-in templates before using it.

Example
-------
::

    from agent_vertical.templates import load_all_templates, get_default_registry

    load_all_templates()
    registry = get_default_registry()
    template = registry.get("clinical_documentation")
"""
from __future__ import annotations

from agent_vertical.templates.base import (
    DomainTemplate,
    TemplateNotFoundError,
    TemplateRegistry,
    get_default_registry,
    load_all_templates,
)

__all__ = [
    "DomainTemplate",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "get_default_registry",
    "load_all_templates",
]
