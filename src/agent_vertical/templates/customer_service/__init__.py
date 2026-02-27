"""Customer service domain template package.

Provides production-ready customer service agent configurations with
escalation policy, tone guardrails, and PII protection defaults.
"""
from __future__ import annotations

from agent_vertical.templates.customer_service.agent import (
    CustomerServiceAgentConfig,
    build_customer_service_config,
)

__all__ = [
    "CustomerServiceAgentConfig",
    "build_customer_service_config",
]
