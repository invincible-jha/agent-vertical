"""Compliance-certified domain templates for agent-vertical.

This package provides production-ready, compliance-annotated agent templates
for regulated and high-trust domains.  Each template bundles a system prompt,
tool configurations, safety rules with regex patterns, evaluation benchmarks,
and structured compliance evidence stubs.

Public API
----------
::

    from agent_vertical.certified import TemplateLibrary
    from agent_vertical.certified.schema import ComplianceFramework, DomainTemplate
    from agent_vertical.certified.validator import TemplateValidator

    library = TemplateLibrary()
    template = library.get_template("healthcare_hipaa")

    validator = TemplateValidator()
    result = validator.validate(template)
    print(result.valid, result.errors)
"""
from __future__ import annotations

from agent_vertical.certified.library import TemplateLibrary
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

__all__ = [
    "ComplianceFramework",
    "DomainTemplate",
    "EvalBenchmark",
    "RiskLevel",
    "SafetyRule",
    "TemplateLibrary",
    "TemplateMetadata",
    "TemplateValidator",
    "ToolConfig",
    "ValidationResult",
]
