"""Grounding validator — verify that agent responses are grounded in source material.

:class:`GroundingValidator` compares the sentences in a generated response
against a set of source texts using token-level Jaccard overlap.  Each
sentence is checked for grounding and an overall grounding score is
returned via :class:`GroundingResult`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


def _tokenise(text: str) -> frozenset[str]:
    """Lower-case and tokenise text into a set of word tokens."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def _sentence_overlap(sentence_tokens: frozenset[str], source_tokens: frozenset[str]) -> float:
    """Compute Jaccard similarity between two token sets.

    Returns 0.0 if either set is empty.
    """
    if not sentence_tokens or not source_tokens:
        return 0.0
    intersection = sentence_tokens & source_tokens
    union = sentence_tokens | source_tokens
    return len(intersection) / len(union)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple punctuation rules."""
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if s.strip()]


@dataclass(frozen=True)
class SentenceGrounding:
    """Grounding result for a single sentence.

    Attributes
    ----------
    sentence:
        The sentence from the agent response.
    max_overlap:
        The highest overlap score achieved against any source text.
    best_source_index:
        Index into the sources list of the best-matching source, or -1 if
        no sources were provided.
    is_grounded:
        Whether ``max_overlap`` meets the grounding threshold.
    """

    sentence: str
    max_overlap: float
    best_source_index: int
    is_grounded: bool


@dataclass
class GroundingResult:
    """Result of a grounding validation run.

    Attributes
    ----------
    response:
        The full agent response that was validated.
    sources:
        The source texts used for validation.
    grounding_score:
        Overall score in [0.0, 1.0] — the fraction of sentences that are
        grounded.
    is_grounded:
        Whether ``grounding_score`` meets the minimum threshold.
    sentence_results:
        Per-sentence grounding details.
    ungrounded_sentences:
        Subset of sentences that did not meet the threshold.
    threshold:
        The overlap threshold that was applied.
    """

    response: str
    sources: list[str]
    grounding_score: float
    is_grounded: bool
    sentence_results: list[SentenceGrounding] = field(default_factory=list)
    ungrounded_sentences: list[str] = field(default_factory=list)
    threshold: float = 0.25


class GroundingValidator:
    """Validate that an agent response is grounded in its source documents.

    Grounding is assessed at the sentence level using token-level Jaccard
    overlap between each response sentence and the concatenated source corpus.
    A sentence is considered grounded if its overlap with the best-matching
    source meets or exceeds ``sentence_threshold``.

    The overall ``grounding_score`` is the proportion of sentences that pass
    the sentence-level threshold.  The response as a whole is considered
    grounded when ``grounding_score >= response_threshold``.

    Parameters
    ----------
    sentence_threshold:
        Minimum Jaccard overlap for a sentence to be considered grounded.
        Default: 0.25.
    response_threshold:
        Minimum fraction of grounded sentences for the whole response to
        be considered grounded.  Default: 0.70.

    Example
    -------
    ::

        validator = GroundingValidator()
        result = validator.validate(
            response="Aspirin inhibits COX enzymes and reduces inflammation.",
            sources=["Aspirin is an NSAID that inhibits COX-1 and COX-2."],
        )
        print(result.is_grounded, result.grounding_score)
    """

    def __init__(
        self,
        sentence_threshold: float = 0.25,
        response_threshold: float = 0.70,
    ) -> None:
        if not (0.0 <= sentence_threshold <= 1.0):
            raise ValueError(
                f"sentence_threshold must be in [0.0, 1.0], got {sentence_threshold!r}"
            )
        if not (0.0 <= response_threshold <= 1.0):
            raise ValueError(
                f"response_threshold must be in [0.0, 1.0], got {response_threshold!r}"
            )
        self._sentence_threshold = sentence_threshold
        self._response_threshold = response_threshold

    def validate(
        self,
        response: str,
        sources: list[str],
    ) -> GroundingResult:
        """Validate that ``response`` is grounded in ``sources``.

        Parameters
        ----------
        response:
            The full text of the agent response to validate.
        sources:
            List of source document texts to check grounding against.

        Returns
        -------
        GroundingResult
            Detailed grounding analysis with per-sentence breakdown.
        """
        sentences = _split_sentences(response)

        if not sentences:
            return GroundingResult(
                response=response,
                sources=sources,
                grounding_score=1.0,
                is_grounded=True,
                sentence_results=[],
                ungrounded_sentences=[],
                threshold=self._sentence_threshold,
            )

        # Pre-tokenise sources for efficiency
        source_token_sets: list[frozenset[str]] = [
            _tokenise(source) for source in sources
        ]

        sentence_results: list[SentenceGrounding] = []

        for sentence in sentences:
            sentence_tokens = _tokenise(sentence)
            max_overlap = 0.0
            best_source_index = -1

            for index, source_tokens in enumerate(source_token_sets):
                overlap = _sentence_overlap(sentence_tokens, source_tokens)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_source_index = index

            is_grounded = max_overlap >= self._sentence_threshold
            sentence_results.append(
                SentenceGrounding(
                    sentence=sentence,
                    max_overlap=max_overlap,
                    best_source_index=best_source_index,
                    is_grounded=is_grounded,
                )
            )

        grounded_count = sum(1 for sr in sentence_results if sr.is_grounded)
        grounding_score = grounded_count / len(sentence_results)
        is_grounded = grounding_score >= self._response_threshold

        ungrounded_sentences = [
            sr.sentence for sr in sentence_results if not sr.is_grounded
        ]

        return GroundingResult(
            response=response,
            sources=sources,
            grounding_score=grounding_score,
            is_grounded=is_grounded,
            sentence_results=sentence_results,
            ungrounded_sentences=ungrounded_sentences,
            threshold=self._sentence_threshold,
        )
