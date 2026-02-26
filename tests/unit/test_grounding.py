"""Tests for grounding modules: citation, validator, claim_tracer, disclaimer,
source_tracker, knowledge_base."""
from __future__ import annotations

import pytest

from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.grounding.citation import Citation, CitationGenerator
from agent_vertical.grounding.claim_tracer import ClaimTrace, ClaimTracer
from agent_vertical.grounding.disclaimer import DisclaimerGenerator
from agent_vertical.grounding.knowledge_base import InMemoryKB, KnowledgeEntry
from agent_vertical.grounding.source_tracker import SourceReference, SourceTracker
from agent_vertical.grounding.validator import (
    GroundingResult,
    GroundingValidator,
    SentenceGrounding,
    _sentence_overlap,
    _split_sentences,
    _tokenise,
)


# ---------------------------------------------------------------------------
# Helper functions: _tokenise, _sentence_overlap, _split_sentences
# ---------------------------------------------------------------------------

class TestTokenise:
    def test_lower_case(self) -> None:
        tokens = _tokenise("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_strips_punctuation(self) -> None:
        tokens = _tokenise("Hello, World!")
        assert "hello" in tokens
        assert "world" in tokens

    def test_numbers_included(self) -> None:
        tokens = _tokenise("Step 2 of process")
        assert "2" in tokens

    def test_empty_string(self) -> None:
        tokens = _tokenise("")
        assert len(tokens) == 0

    def test_returns_frozenset(self) -> None:
        result = _tokenise("some text")
        assert isinstance(result, frozenset)


class TestSentenceOverlap:
    def test_identical_sets(self) -> None:
        tokens = frozenset({"aspirin", "inhibits", "cox"})
        assert _sentence_overlap(tokens, tokens) == 1.0

    def test_no_overlap(self) -> None:
        a = frozenset({"cat", "dog"})
        b = frozenset({"fish", "bird"})
        assert _sentence_overlap(a, b) == 0.0

    def test_partial_overlap(self) -> None:
        a = frozenset({"a", "b", "c"})
        b = frozenset({"a", "b", "d"})
        overlap = _sentence_overlap(a, b)
        # intersection={a,b}, union={a,b,c,d} => 2/4 = 0.5
        assert abs(overlap - 0.5) < 1e-9

    def test_empty_sentence_tokens(self) -> None:
        assert _sentence_overlap(frozenset(), frozenset({"a"})) == 0.0

    def test_empty_source_tokens(self) -> None:
        assert _sentence_overlap(frozenset({"a"}), frozenset()) == 0.0


class TestSplitSentences:
    def test_single_sentence(self) -> None:
        sentences = _split_sentences("This is a sentence.")
        assert len(sentences) == 1

    def test_multiple_sentences(self) -> None:
        sentences = _split_sentences("First sentence. Second sentence.")
        assert len(sentences) == 2

    def test_question_mark(self) -> None:
        sentences = _split_sentences("Is this? Yes it is.")
        assert len(sentences) == 2

    def test_exclamation_mark(self) -> None:
        sentences = _split_sentences("Stop! Look around.")
        assert len(sentences) == 2

    def test_empty_string(self) -> None:
        sentences = _split_sentences("")
        assert sentences == []

    def test_strips_whitespace(self) -> None:
        sentences = _split_sentences("  Hello world.  ")
        assert all(s == s.strip() for s in sentences)


# ---------------------------------------------------------------------------
# GroundingValidator
# ---------------------------------------------------------------------------

class TestGroundingValidator:
    def test_default_construction(self) -> None:
        validator = GroundingValidator()
        assert validator._sentence_threshold == 0.25
        assert validator._response_threshold == 0.70

    def test_invalid_sentence_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="sentence_threshold"):
            GroundingValidator(sentence_threshold=1.5)

    def test_invalid_response_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="response_threshold"):
            GroundingValidator(response_threshold=-0.1)

    def test_empty_response_is_grounded(self) -> None:
        validator = GroundingValidator()
        result = validator.validate(response="", sources=["some source"])
        assert result.is_grounded is True
        assert result.grounding_score == 1.0

    def test_grounded_response(self) -> None:
        validator = GroundingValidator(sentence_threshold=0.1)
        source = "Aspirin inhibits COX enzymes and reduces inflammation."
        response = "Aspirin inhibits COX and reduces inflammation."
        result = validator.validate(response=response, sources=[source])
        assert result.grounding_score > 0.0

    def test_ungrounded_response(self) -> None:
        validator = GroundingValidator(sentence_threshold=0.9)
        source = "Bananas are yellow fruits."
        response = "Quantum computing uses qubits."
        result = validator.validate(response=response, sources=[source])
        assert result.grounding_score < 1.0
        assert len(result.ungrounded_sentences) > 0

    def test_sentence_results_populated(self) -> None:
        validator = GroundingValidator()
        result = validator.validate(
            response="First sentence. Second sentence.",
            sources=["First sentence context."],
        )
        assert len(result.sentence_results) == 2

    def test_threshold_stored(self) -> None:
        validator = GroundingValidator(sentence_threshold=0.3)
        result = validator.validate(response="Hello.", sources=["world"])
        assert result.threshold == 0.3

    def test_no_sources_results_in_ungrounded(self) -> None:
        validator = GroundingValidator()
        result = validator.validate(response="Some claim here.", sources=[])
        assert result.grounding_score == 0.0

    def test_best_source_index_set(self) -> None:
        validator = GroundingValidator(sentence_threshold=0.0)
        sources = ["apples and oranges", "cars and trucks"]
        result = validator.validate(
            response="Apples and oranges are fruits.", sources=sources
        )
        first_sr = result.sentence_results[0]
        assert isinstance(first_sr, SentenceGrounding)
        assert first_sr.best_source_index in (0, 1)


# ---------------------------------------------------------------------------
# SourceTracker and SourceReference
# ---------------------------------------------------------------------------

class TestSourceReference:
    def test_create_sets_timestamp(self) -> None:
        ref = SourceReference.create(
            claim="Aspirin inhibits COX.",
            source_id="ref-001",
            source_title="Pharmacology",
            confidence=0.9,
        )
        assert ref.tracked_at != ""

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            SourceReference(
                claim="test",
                source_id="id",
                source_title="title",
                confidence=1.5,
            )

    def test_zero_confidence_valid(self) -> None:
        ref = SourceReference(
            claim="test",
            source_id="id",
            source_title="title",
            confidence=0.0,
        )
        assert ref.confidence == 0.0


class TestSourceTracker:
    def test_track_adds_reference(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim", "src-001", "My Source", 0.8)
        assert len(tracker) == 1

    def test_get_references_returns_list(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim", "src-001", "My Source", 0.8)
        refs = tracker.get_references()
        assert isinstance(refs, list)
        assert refs[0].source_id == "src-001"

    def test_references_for_source(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim A", "src-001", "Source A", 0.8)
        tracker.track("claim B", "src-002", "Source B", 0.7)
        tracker.track("claim C", "src-001", "Source A", 0.9)
        refs = tracker.references_for_source("src-001")
        assert len(refs) == 2

    def test_unique_sources(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim A", "src-001", "A", 0.9)
        tracker.track("claim B", "src-001", "A", 0.8)
        tracker.track("claim C", "src-002", "B", 0.7)
        sources = tracker.unique_sources()
        assert sources == ["src-001", "src-002"]

    def test_clear_resets_tracker(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim", "src-001", "A", 0.9)
        tracker.clear()
        assert len(tracker) == 0

    def test_repr_contains_count(self) -> None:
        tracker = SourceTracker()
        tracker.track("c", "id", "t", 0.5)
        repr_str = repr(tracker)
        assert "1" in repr_str


# ---------------------------------------------------------------------------
# CitationGenerator
# ---------------------------------------------------------------------------

class TestCitationGenerator:
    def _make_tracker_with_refs(self) -> SourceTracker:
        tracker = SourceTracker()
        tracker.track("Aspirin inhibits COX.", "ref-001", "Pharmacology Text", 0.95)
        tracker.track("Ibuprofen is an NSAID.", "ref-002", "Drug Reference", 0.90)
        return tracker

    def test_get_citations_returns_all(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        citations = gen.get_citations()
        assert len(citations) == 2

    def test_citation_numbers_are_sequential(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        numbers = [c.number for c in gen.get_citations()]
        assert numbers == [1, 2]

    def test_duplicate_sources_single_citation(self) -> None:
        tracker = SourceTracker()
        tracker.track("Claim A", "ref-001", "Source", 0.9)
        tracker.track("Claim B", "ref-001", "Source", 0.8)
        gen = CitationGenerator(tracker.get_references())
        assert len(gen.get_citations()) == 1

    def test_citation_for_source_returns_citation(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        citation = gen.citation_for_source("ref-001")
        assert citation is not None
        assert citation.number == 1

    def test_citation_for_unknown_source_returns_none(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        assert gen.citation_for_source("nonexistent") is None

    def test_inline_marker_format(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim", "ref-001", "Title", 0.9)
        gen = CitationGenerator(tracker.get_references())
        assert gen.inline_marker("ref-001") == "[1]"

    def test_inline_marker_unknown_source_empty(self) -> None:
        gen = CitationGenerator([])
        assert gen.inline_marker("unknown") == ""

    def test_generate_bibliography_with_sources(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        bib = gen.generate_bibliography()
        assert "[1]" in bib
        assert "[2]" in bib
        assert "Pharmacology Text" in bib

    def test_generate_bibliography_no_sources(self) -> None:
        gen = CitationGenerator([])
        bib = gen.generate_bibliography()
        assert "No sources cited" in bib

    def test_generate_bibliography_custom_header(self) -> None:
        tracker = SourceTracker()
        tracker.track("claim", "ref-001", "Title", 0.9)
        gen = CitationGenerator(tracker.get_references())
        bib = gen.generate_bibliography(header="Sources")
        assert bib.startswith("Sources")

    def test_annotate_response_empty_response(self) -> None:
        tracker = self._make_tracker_with_refs()
        gen = CitationGenerator(tracker.get_references())
        result = gen.annotate_response("")
        assert result == ""

    def test_annotate_response_no_references(self) -> None:
        gen = CitationGenerator([])
        response = "Some response text."
        assert gen.annotate_response(response) == response

    def test_annotate_response_injects_marker(self) -> None:
        tracker = SourceTracker()
        tracker.track(
            "Aspirin inhibits COX enzymes",
            "ref-001",
            "Pharmacology Text",
            0.95,
        )
        gen = CitationGenerator(tracker.get_references())
        annotated = gen.annotate_response(
            "Aspirin inhibits COX enzymes and reduces inflammation."
        )
        assert "[1]" in annotated

    def test_bibliography_excerpt_truncated(self) -> None:
        long_excerpt = "A" * 200
        tracker = SourceTracker()
        tracker.track("claim", "ref-001", "Title", 0.9, excerpt=long_excerpt)
        gen = CitationGenerator(tracker.get_references())
        bib = gen.generate_bibliography()
        assert "..." in bib


# ---------------------------------------------------------------------------
# ClaimTracer
# ---------------------------------------------------------------------------

class TestClaimTracer:
    def test_trace_returns_claim_trace(self) -> None:
        tracer = ClaimTracer()
        trace = tracer.trace("Claim text", ["entry-001"], 0.85)
        assert isinstance(trace, ClaimTrace)
        assert trace.claim == "Claim text"

    def test_claim_id_sequential(self) -> None:
        tracer = ClaimTracer()
        t1 = tracer.trace("Claim 1", ["e1"], 0.9)
        t2 = tracer.trace("Claim 2", ["e2"], 0.8)
        assert t1.claim_id == "claim-0001"
        assert t2.claim_id == "claim-0002"

    def test_invalid_confidence_raises(self) -> None:
        tracer = ClaimTracer()
        with pytest.raises(ValueError, match="confidence"):
            tracer.trace("claim", ["entry"], 1.5)

    def test_get_traces_returns_all(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("C1", ["e1"], 0.9)
        tracer.trace("C2", ["e2"], 0.8)
        traces = tracer.get_traces()
        assert len(traces) == 2

    def test_traces_for_entry(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("Claim A", ["entry-001", "entry-002"], 0.9)
        tracer.trace("Claim B", ["entry-003"], 0.8)
        result = tracer.traces_for_entry("entry-001")
        assert len(result) == 1
        assert result[0].claim == "Claim A"

    def test_low_confidence_traces(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("High conf", ["e1"], 0.9)
        tracer.trace("Low conf", ["e2"], 0.5)
        low = tracer.low_confidence_traces(threshold=0.7)
        assert len(low) == 1
        assert low[0].claim == "Low conf"

    def test_clear_resets_tracer(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("Claim", ["e1"], 0.9)
        tracer.clear()
        assert len(tracer) == 0

    def test_clear_resets_counter(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("Claim", ["e1"], 0.9)
        tracer.clear()
        trace = tracer.trace("New claim", ["e2"], 0.8)
        assert trace.claim_id == "claim-0001"

    def test_repr_contains_count(self) -> None:
        tracer = ClaimTracer()
        tracer.trace("C", ["e"], 0.5)
        assert "1" in repr(tracer)

    def test_reasoning_stored(self) -> None:
        tracer = ClaimTracer()
        trace = tracer.trace("Claim", ["e1"], 0.9, reasoning="Because X")
        assert trace.reasoning == "Because X"

    def test_traced_at_set(self) -> None:
        tracer = ClaimTracer()
        trace = tracer.trace("Claim", ["e1"], 0.9)
        assert trace.traced_at != ""

    def test_supporting_entry_ids_as_tuple(self) -> None:
        tracer = ClaimTracer()
        trace = tracer.trace("Claim", ["a", "b", "c"], 0.9)
        assert isinstance(trace.supporting_entry_ids, tuple)
        assert trace.supporting_entry_ids == ("a", "b", "c")


# ---------------------------------------------------------------------------
# DisclaimerGenerator
# ---------------------------------------------------------------------------

class TestDisclaimerGenerator:
    def test_healthcare_informational(self) -> None:
        gen = DisclaimerGenerator("healthcare", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "DISCLAIMER" in disclaimer
        assert "medical" in disclaimer.lower()

    def test_healthcare_advisory(self) -> None:
        gen = DisclaimerGenerator("healthcare", RiskTier.ADVISORY)
        disclaimer = gen.get_disclaimer()
        assert "clinician" in disclaimer.lower()

    def test_healthcare_decision_support(self) -> None:
        gen = DisclaimerGenerator("healthcare", RiskTier.DECISION_SUPPORT)
        disclaimer = gen.get_disclaimer()
        assert "DISCLAIMER" in disclaimer

    def test_finance_domain(self) -> None:
        gen = DisclaimerGenerator("finance", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "investment" in disclaimer.lower()

    def test_legal_domain(self) -> None:
        gen = DisclaimerGenerator("legal", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "legal" in disclaimer.lower()

    def test_education_domain(self) -> None:
        gen = DisclaimerGenerator("education", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "NOTE" in disclaimer

    def test_unknown_domain_falls_back_to_generic(self) -> None:
        gen = DisclaimerGenerator("unknown_domain", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "DISCLAIMER" in disclaimer

    def test_append_to_response(self) -> None:
        gen = DisclaimerGenerator("healthcare", RiskTier.INFORMATIONAL)
        combined = gen.append_to("Response text.")
        assert "Response text." in combined
        assert "DISCLAIMER" in combined

    def test_append_to_custom_separator(self) -> None:
        gen = DisclaimerGenerator("healthcare", RiskTier.INFORMATIONAL)
        combined = gen.append_to("Response", separator=" | ")
        assert " | " in combined

    def test_available_domains_returns_list(self) -> None:
        domains = DisclaimerGenerator.available_domains()
        assert isinstance(domains, list)
        assert "healthcare" in domains
        assert "finance" in domains
        assert "legal" in domains
        assert "education" in domains

    def test_available_domains_sorted(self) -> None:
        domains = DisclaimerGenerator.available_domains()
        assert domains == sorted(domains)

    def test_domain_case_insensitive(self) -> None:
        gen = DisclaimerGenerator("HEALTHCARE", RiskTier.INFORMATIONAL)
        disclaimer = gen.get_disclaimer()
        assert "DISCLAIMER" in disclaimer


# ---------------------------------------------------------------------------
# KnowledgeBase (InMemoryKB)
# ---------------------------------------------------------------------------

class TestInMemoryKB:
    def _make_entry(self, entry_id: str = "e-001", title: str = "Title", content: str = "Content") -> KnowledgeEntry:
        return KnowledgeEntry(
            entry_id=entry_id,
            title=title,
            content=content,
            source_id="src-001",
            tags=["tag1", "tag2"],
        )

    def test_add_and_get(self) -> None:
        kb = InMemoryKB()
        entry = self._make_entry()
        kb.add(entry)
        retrieved = kb.get("e-001")
        assert retrieved is not None
        assert retrieved.title == "Title"

    def test_get_missing_returns_none(self) -> None:
        kb = InMemoryKB()
        assert kb.get("nonexistent") is None

    def test_remove_existing(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry())
        assert kb.remove("e-001") is True
        assert kb.get("e-001") is None

    def test_remove_nonexistent_returns_false(self) -> None:
        kb = InMemoryKB()
        assert kb.remove("nonexistent") is False

    def test_search_by_content(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry(entry_id="e-001", content="Aspirin reduces inflammation"))
        kb.add(self._make_entry(entry_id="e-002", content="Ibuprofen is an NSAID"))
        results = kb.search("aspirin")
        assert len(results) == 1
        assert results[0].entry_id == "e-001"

    def test_search_by_title(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry(entry_id="e-001", title="HIPAA Overview", content="Details..."))
        results = kb.search("hipaa")
        assert len(results) == 1

    def test_search_with_tag_filter(self) -> None:
        kb = InMemoryKB()
        entry_a = KnowledgeEntry(entry_id="a", title="A", content="content", tags=["hipaa"])
        entry_b = KnowledgeEntry(entry_id="b", title="B content", content="content", tags=["gdpr"])
        kb.add(entry_a)
        kb.add(entry_b)
        results = kb.search("content", tags=["hipaa"])
        assert len(results) == 1
        assert results[0].entry_id == "a"

    def test_search_no_match(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry())
        results = kb.search("completely unrelated zxqwerty")
        assert results == []

    def test_all_entries(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry("e1"))
        kb.add(self._make_entry("e2"))
        entries = kb.all_entries()
        assert len(entries) == 2

    def test_len(self) -> None:
        kb = InMemoryKB()
        assert len(kb) == 0
        kb.add(self._make_entry("e1"))
        assert len(kb) == 1

    def test_repr(self) -> None:
        kb = InMemoryKB()
        kb.add(self._make_entry("e1"))
        assert "InMemoryKB" in repr(kb)
        assert "1" in repr(kb)

    def test_add_overwrites_existing(self) -> None:
        kb = InMemoryKB()
        kb.add(KnowledgeEntry(entry_id="e1", title="Old", content="old content"))
        kb.add(KnowledgeEntry(entry_id="e1", title="New", content="new content"))
        assert kb.get("e1").title == "New"
