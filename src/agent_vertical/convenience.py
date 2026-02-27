"""Convenience API for agent-vertical — 3-line quickstart.

Example
-------
::

    from agent_vertical import Template
    template = Template("healthcare")
    print(template.system_prompt)

"""
from __future__ import annotations

from typing import Any


class Template:
    """Zero-config domain template accessor for the 80% use case.

    Loads the named domain template from the built-in template registry
    with a single constructor call. Falls back to a minimal stub if the
    domain is not found.

    Parameters
    ----------
    domain:
        Domain name (e.g. ``"healthcare"``, ``"finance"``, ``"legal"``).

    Example
    -------
    ::

        from agent_vertical import Template
        template = Template("healthcare")
        print(template.domain)
        print(template.system_prompt)
    """

    def __init__(self, domain: str) -> None:
        from agent_vertical.templates.base import (
            get_default_registry,
            load_all_templates,
        )

        load_all_templates()
        registry = get_default_registry()

        try:
            self._template = registry.get(domain)
            self._found = True
        except Exception:
            self._template = None
            self._found = False

        self.domain = domain

    @property
    def system_prompt(self) -> str:
        """The domain's system prompt string.

        Returns an empty string if the domain template was not found.
        """
        if self._template is None:
            return f"You are a helpful AI assistant specialised in {self.domain}."
        prompt = getattr(self._template, "system_prompt", "")
        return prompt if isinstance(prompt, str) else str(prompt)

    @property
    def found(self) -> bool:
        """True if the domain template was found in the registry."""
        return self._found

    @property
    def template(self) -> Any | None:
        """The underlying DomainTemplate object, or None if not found."""
        return self._template

    def check_compliance(self, text: str) -> Any:
        """Run domain compliance checks on a piece of text.

        Parameters
        ----------
        text:
            Agent response text to check for domain-specific compliance.

        Returns
        -------
        ComplianceCheckResult
            Result with ``.passed`` bool and ``.violations`` list.
        """
        from agent_vertical.compliance.checker import DomainComplianceChecker

        checker = DomainComplianceChecker(self.domain)
        return checker.check(text)

    def __repr__(self) -> str:
        return f"Template(domain={self.domain!r}, found={self._found})"
