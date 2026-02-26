"""Citation generator — inline [N] style citations and bibliography.

:class:`CitationGenerator` accepts a list of :class:`SourceReference` objects
and injects inline numeric citations into response text, then generates a
formatted bibliography.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent_vertical.grounding.source_tracker import SourceReference


@dataclass(frozen=True)
class Citation:
    """A single citation entry.

    Attributes
    ----------
    number:
        The inline citation number (1-indexed).
    source_id:
        Unique source identifier.
    source_title:
        Human-readable title of the source.
    excerpt:
        Optional supporting excerpt.
    """

    number: int
    source_id: str
    source_title: str
    excerpt: str = ""


class CitationGenerator:
    """Generate inline [N] citations and a bibliography from source references.

    The generator assigns a citation number to each unique source in the
    order it first appears in the reference list.  Inline citations are
    appended to the relevant sentence or injected at marked positions.

    Parameters
    ----------
    references:
        Ordered list of :class:`SourceReference` objects produced by
        :class:`~agent_vertical.grounding.source_tracker.SourceTracker`.

    Example
    -------
    ::

        from agent_vertical.grounding.source_tracker import SourceTracker

        tracker = SourceTracker()
        tracker.track("Aspirin inhibits COX enzymes.", "ref-001", "Pharmacology Text", 0.95)
        tracker.track("Ibuprofen is an NSAID.", "ref-002", "Drug Reference", 0.90)

        generator = CitationGenerator(tracker.get_references())
        print(generator.generate_bibliography())
    """

    def __init__(self, references: list[SourceReference]) -> None:
        self._references = references
        self._citations: list[Citation] = self._build_citations(references)
        # Map from source_id to Citation for fast lookup
        self._citation_map: dict[str, Citation] = {
            c.source_id: c for c in self._citations
        }

    @staticmethod
    def _build_citations(references: list[SourceReference]) -> list[Citation]:
        """Assign sequential numbers to unique sources in order of first appearance."""
        seen: dict[str, Citation] = {}
        citations: list[Citation] = []
        counter = 1
        for ref in references:
            if ref.source_id not in seen:
                citation = Citation(
                    number=counter,
                    source_id=ref.source_id,
                    source_title=ref.source_title,
                    excerpt=ref.excerpt,
                )
                seen[ref.source_id] = citation
                citations.append(citation)
                counter += 1
        return citations

    def get_citations(self) -> list[Citation]:
        """Return all unique citations in citation-number order.

        Returns
        -------
        list[Citation]
        """
        return list(self._citations)

    def citation_for_source(self, source_id: str) -> Citation | None:
        """Return the :class:`Citation` for a source ID, or ``None`` if unknown.

        Parameters
        ----------
        source_id:
            The source identifier to look up.

        Returns
        -------
        Citation | None
        """
        return self._citation_map.get(source_id)

    def inline_marker(self, source_id: str) -> str:
        """Return the inline citation marker for a source (e.g. ``"[1]"``).

        Parameters
        ----------
        source_id:
            The source identifier.

        Returns
        -------
        str
            The formatted citation marker, or an empty string if the source
            is not in the citation list.
        """
        citation = self._citation_map.get(source_id)
        if citation is None:
            return ""
        return f"[{citation.number}]"

    def annotate_response(self, response: str) -> str:
        """Append inline citation markers to sentences in ``response``.

        Each source reference is matched to a sentence in the response using
        substring matching on the claim text.  When a match is found, the
        citation marker is appended immediately after the matched sentence.

        Sentences with no matching reference are returned unchanged.

        Parameters
        ----------
        response:
            The full agent response text.

        Returns
        -------
        str
            The response with inline citation markers inserted.
        """
        if not self._references or not response:
            return response

        annotated = response
        for ref in self._references:
            citation = self._citation_map.get(ref.source_id)
            if citation is None:
                continue
            marker = f"[{citation.number}]"
            # Find the claim within the response and append the marker
            # after the sentence-ending punctuation if present.
            claim_pattern = re.escape(ref.claim[:40])  # match on first 40 chars
            match = re.search(claim_pattern, annotated, re.IGNORECASE)
            if match:
                end = match.end()
                # Advance to end of sentence if possible
                sentence_end = re.search(r"[.!?]", annotated[end:])
                insert_pos = (end + sentence_end.end()) if sentence_end else end
                # Only add marker if not already present immediately after
                window = annotated[insert_pos : insert_pos + 10]
                if marker not in window:
                    annotated = annotated[:insert_pos] + " " + marker + annotated[insert_pos:]
        return annotated

    def generate_bibliography(self, header: str = "References") -> str:
        """Generate a formatted numbered bibliography.

        Parameters
        ----------
        header:
            The section header to prepend to the bibliography.

        Returns
        -------
        str
            A formatted bibliography string.

        Example output::

            References
            [1] Pharmacology Text
            [2] Drug Reference — "Ibuprofen is an NSAID..."
        """
        if not self._citations:
            return f"{header}\n(No sources cited.)"

        lines: list[str] = [header]
        for citation in sorted(self._citations, key=lambda c: c.number):
            entry = f"[{citation.number}] {citation.source_title}"
            if citation.excerpt:
                # Truncate long excerpts for readability
                excerpt = citation.excerpt[:120]
                if len(citation.excerpt) > 120:
                    excerpt += "..."
                entry += f' — "{excerpt}"'
            lines.append(entry)
        return "\n".join(lines)
