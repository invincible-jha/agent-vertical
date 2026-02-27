"""Cross-AumOS integration templates subpackage."""
from __future__ import annotations

from agent_vertical.integrations.aumos_templates import (
    AumOSComponent,
    IntegrationBinding,
    IntegrationTemplate,
    IntegrationTemplateRegistry,
    build_integration_config,
)

__all__ = [
    "AumOSComponent",
    "IntegrationBinding",
    "IntegrationTemplate",
    "IntegrationTemplateRegistry",
    "build_integration_config",
]
