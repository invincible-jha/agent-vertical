"""Shared bootstrap for agent-vertical benchmarks."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SRC = _REPO_ROOT / "src"
_BENCHMARKS = _REPO_ROOT / "benchmarks"

for _path in [str(_SRC), str(_BENCHMARKS)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.templates.base import DomainTemplate, TemplateRegistry, load_all_templates

__all__ = ["RiskTier", "DomainTemplate", "TemplateRegistry", "load_all_templates"]
