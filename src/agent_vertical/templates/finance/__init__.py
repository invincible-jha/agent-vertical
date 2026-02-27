"""Finance domain template package.

Provides PCI-DSS and SOX-aware production-ready finance agent configurations
with compliance guardrails for regulated financial environments.
"""
from __future__ import annotations

from agent_vertical.templates.finance.agent import (
    FinanceAgentConfig,
    build_finance_config,
)

__all__ = [
    "FinanceAgentConfig",
    "build_finance_config",
]
