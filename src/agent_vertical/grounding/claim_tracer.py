"""Claim tracer — trace individual factual claims through a response.

:class:`ClaimTracer` records which knowledge base entries or source documents
support each claim made in an agent response.  This provides fine-grained
provenance beyond document-level attribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ClaimTrace:
    """A single traced claim with its supporting evidence.

    Attributes
    ----------
    claim_id:
        Unique identifier for this claim trace (auto-assigned).
    claim:
        The verbatim or paraphrased claim text.
    supporting_entry_ids:
        Knowledge base entry IDs that support this claim.
    confidence:
        Overall confidence in the claim's accuracy, in [0.0, 1.0].
    reasoning:
        Optional explanation of why the cited entries support this claim.
    traced_at:
        ISO 8601 timestamp when this trace was recorded.
    """

    claim_id: str
    claim: str
    supporting_entry_ids: tuple[str, ...]
    confidence: float
    reasoning: str = ""
    traced_at: str = ""


class ClaimTracer:
    """Trace factual claims in an agent response to their source entries.

    Attach a :class:`ClaimTracer` to an agent's response-generation pipeline
    to build a full claim-level provenance record.

    Example
    -------
    ::

        tracer = ClaimTracer()
        tracer.trace(
            claim="The standard ICU nurse-to-patient ratio is 1:2.",
            supporting_entry_ids=["icu-staffing-001", "ahna-guidelines-2023"],
            confidence=0.88,
            reasoning="Both entries cite the same AHRQ staffing guideline.",
        )
        traces = tracer.get_traces()
    """

    def __init__(self) -> None:
        self._traces: list[ClaimTrace] = []
        self._counter: int = 0

    def trace(
        self,
        claim: str,
        supporting_entry_ids: list[str],
        confidence: float,
        reasoning: str = "",
    ) -> ClaimTrace:
        """Record a claim trace.

        Parameters
        ----------
        claim:
            The factual claim being traced.
        supporting_entry_ids:
            Knowledge base or source entry IDs that support this claim.
        confidence:
            Confidence that the cited entries substantiate the claim; [0.0, 1.0].
        reasoning:
            Optional explanation of the relationship between claim and evidence.

        Returns
        -------
        ClaimTrace
            The recorded trace.

        Raises
        ------
        ValueError
            If ``confidence`` is outside [0.0, 1.0].
        """
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {confidence!r}"
            )
        self._counter += 1
        trace = ClaimTrace(
            claim_id=f"claim-{self._counter:04d}",
            claim=claim,
            supporting_entry_ids=tuple(supporting_entry_ids),
            confidence=confidence,
            reasoning=reasoning,
            traced_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._traces.append(trace)
        return trace

    def get_traces(self) -> list[ClaimTrace]:
        """Return all recorded traces in insertion order.

        Returns
        -------
        list[ClaimTrace]
        """
        return list(self._traces)

    def traces_for_entry(self, entry_id: str) -> list[ClaimTrace]:
        """Return traces whose supporting entries include ``entry_id``.

        Parameters
        ----------
        entry_id:
            The knowledge base entry ID to filter on.

        Returns
        -------
        list[ClaimTrace]
        """
        return [t for t in self._traces if entry_id in t.supporting_entry_ids]

    def low_confidence_traces(self, threshold: float = 0.70) -> list[ClaimTrace]:
        """Return traces with confidence below ``threshold``.

        Parameters
        ----------
        threshold:
            Confidence cutoff.  Traces with ``confidence < threshold`` are returned.

        Returns
        -------
        list[ClaimTrace]
        """
        return [t for t in self._traces if t.confidence < threshold]

    def clear(self) -> None:
        """Remove all recorded traces and reset the counter."""
        self._traces.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._traces)

    def __repr__(self) -> str:
        return f"ClaimTracer(traces={len(self._traces)})"
