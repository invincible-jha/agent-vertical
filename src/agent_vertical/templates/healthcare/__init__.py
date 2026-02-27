"""Healthcare domain template package.

Provides HIPAA-aware production-ready healthcare agent configurations and
domain templates with clinical safety guardrails.
"""
from __future__ import annotations

from agent_vertical.templates.healthcare.agent import (
    HealthcareAgentConfig,
    build_healthcare_config,
)

__all__ = [
    "HealthcareAgentConfig",
    "build_healthcare_config",
]
