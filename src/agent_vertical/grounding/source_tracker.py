"""Source tracker — track claims to their originating sources.

:class:`SourceTracker` maintains an ordered log of claim-to-source mappings
produced during a single agent response turn.  :class:`SourceReference`
captures the metadata for each tracked claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class SourceReference:
    """A single tracked claim-to-source mapping.

    Attributes
    ----------
    claim:
        The verbatim or paraphrased claim being attributed.
    source_id:
        Unique identifier for the source document or knowledge base entry.
    source_title:
        Human-readable title of the source.
    confidence:
        Confidence score in [0.0, 1.0] that this source supports the claim.
    excerpt:
        Optional verbatim excerpt from the source that supports the claim.
    tracked_at:
        ISO 8601 timestamp of when this reference was recorded.
    """

    claim: str
    source_id: str
    source_title: str
    confidence: float
    excerpt: str = ""
    tracked_at: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence!r}"
            )

    @classmethod
    def create(
        cls,
        claim: str,
        source_id: str,
        source_title: str,
        confidence: float,
        excerpt: str = "",
    ) -> SourceReference:
        """Create a :class:`SourceReference` with the current UTC timestamp.

        Parameters
        ----------
        claim:
            The claim being attributed.
        source_id:
            Unique identifier for the source.
        source_title:
            Human-readable title of the source.
        confidence:
            Confidence score in [0.0, 1.0].
        excerpt:
            Optional verbatim supporting excerpt.

        Returns
        -------
        SourceReference
        """
        return cls(
            claim=claim,
            source_id=source_id,
            source_title=source_title,
            confidence=confidence,
            excerpt=excerpt,
            tracked_at=datetime.now(tz=timezone.utc).isoformat(),
        )


# Alias kept for backwards compatibility with the grounding __init__.py
SourceRecord = SourceReference


class SourceTracker:
    """Track claims to their originating sources within a response turn.

    :class:`SourceTracker` is designed to be instantiated once per agent
    response generation and passed to any component that produces factual
    claims.  After generation completes, call :meth:`get_references` to
    retrieve the full provenance log.

    Example
    -------
    ::

        tracker = SourceTracker()
        tracker.track(
            claim="Aspirin inhibits COX-1 and COX-2 enzymes.",
            source_id="pharmacology-ref-001",
            source_title="Basic and Clinical Pharmacology, 15th ed.",
            confidence=0.95,
            excerpt="Aspirin irreversibly inhibits both COX-1 and COX-2...",
        )
        refs = tracker.get_references()
    """

    def __init__(self) -> None:
        self._references: list[SourceReference] = []

    def track(
        self,
        claim: str,
        source_id: str,
        source_title: str,
        confidence: float,
        excerpt: str = "",
    ) -> SourceReference:
        """Record a claim-to-source mapping.

        Parameters
        ----------
        claim:
            The verbatim or paraphrased claim being attributed.
        source_id:
            Unique identifier for the source document or knowledge base entry.
        source_title:
            Human-readable title of the source.
        confidence:
            Confidence that this source supports the claim; must be in [0.0, 1.0].
        excerpt:
            Optional verbatim excerpt from the source.

        Returns
        -------
        SourceReference
            The newly created reference, also stored internally.

        Raises
        ------
        ValueError
            If ``confidence`` is outside [0.0, 1.0].
        """
        ref = SourceReference.create(
            claim=claim,
            source_id=source_id,
            source_title=source_title,
            confidence=confidence,
            excerpt=excerpt,
        )
        self._references.append(ref)
        return ref

    def get_references(self) -> list[SourceReference]:
        """Return all tracked references in insertion order.

        Returns
        -------
        list[SourceReference]
        """
        return list(self._references)

    def references_for_source(self, source_id: str) -> list[SourceReference]:
        """Return all references attributed to a specific source.

        Parameters
        ----------
        source_id:
            The source identifier to filter on.

        Returns
        -------
        list[SourceReference]
        """
        return [r for r in self._references if r.source_id == source_id]

    def unique_sources(self) -> list[str]:
        """Return a deduplicated list of source IDs in order of first appearance.

        Returns
        -------
        list[str]
        """
        seen: list[str] = []
        for ref in self._references:
            if ref.source_id not in seen:
                seen.append(ref.source_id)
        return seen

    def clear(self) -> None:
        """Remove all tracked references."""
        self._references.clear()

    def __len__(self) -> int:
        return len(self._references)

    def __repr__(self) -> str:
        return f"SourceTracker(references={len(self._references)})"
