"""Grounding subsystem — source tracking, claim tracing, disclaimers, and knowledge bases."""
from __future__ import annotations

from agent_vertical.grounding.citation import Citation, CitationGenerator
from agent_vertical.grounding.claim_tracer import ClaimTrace, ClaimTracer
from agent_vertical.grounding.disclaimer import DisclaimerGenerator
from agent_vertical.grounding.knowledge_base import InMemoryKB, KnowledgeBase
from agent_vertical.grounding.source_tracker import SourceRecord, SourceReference, SourceTracker
from agent_vertical.grounding.validator import GroundingResult, GroundingValidator, SentenceGrounding

__all__ = [
    "Citation",
    "CitationGenerator",
    "ClaimTrace",
    "ClaimTracer",
    "DisclaimerGenerator",
    "GroundingResult",
    "GroundingValidator",
    "InMemoryKB",
    "KnowledgeBase",
    "SentenceGrounding",
    "SourceRecord",
    "SourceReference",
    "SourceTracker",
]
