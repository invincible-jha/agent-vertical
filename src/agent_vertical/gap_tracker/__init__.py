"""Gap tracker subpackage for vertical agent templates."""
from __future__ import annotations

from agent_vertical.gap_tracker.scanner import (
    GapReport,
    GapSeverity,
    TemplateGap,
    TemplateGapScanner,
)

__all__ = [
    "GapReport",
    "GapSeverity",
    "TemplateGap",
    "TemplateGapScanner",
]
