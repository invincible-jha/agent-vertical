"""Tests that cover the remaining small coverage gaps across multiple modules.

This file covers:
- benchmarks.scenarios: by_tag, list_domains, __len__
- certification.risk_tier: __le__ and __ge__ NotImplemented branches
- certification.report: as_text() medium_failures and low_failures branches
- grounding.citation: annotate_response continue branch (source_id not in citation_map)
"""
from __future__ import annotations

import pytest

from agent_vertical.benchmarks.scenarios import ScenarioLibrary
from agent_vertical.certification.evaluator import CertificationEvaluator
from agent_vertical.certification.report import CertificationReporter
from agent_vertical.certification.risk_tier import RiskTier
from agent_vertical.certification.scorer import CheckResult, FindingSeverity
from agent_vertical.grounding.citation import CitationGenerator
from agent_vertical.grounding.source_tracker import SourceReference


# ---------------------------------------------------------------------------
# ScenarioLibrary.by_tag
# ---------------------------------------------------------------------------


class TestScenarioLibraryByTag:
    def test_by_tag_returns_scenarios_with_matching_tag(self) -> None:
        library = ScenarioLibrary()
        # Find all tags used in the library
        all_scenarios = library.all_scenarios()
        all_tags = {tag for s in all_scenarios for tag in s.tags}
        if not all_tags:
            pytest.skip("No tags defined in built-in scenarios")
        tag = next(iter(all_tags))
        results = library.by_tag(tag)
        assert len(results) > 0
        for s in results:
            assert tag in s.tags

    def test_by_tag_unknown_tag_returns_empty(self) -> None:
        library = ScenarioLibrary()
        results = library.by_tag("zzz_nonexistent_tag_xyz")
        assert results == []

    def test_by_tag_sorted_by_id(self) -> None:
        library = ScenarioLibrary()
        all_scenarios = library.all_scenarios()
        all_tags = {tag for s in all_scenarios for tag in s.tags}
        if not all_tags:
            pytest.skip("No tags defined in built-in scenarios")
        tag = next(iter(all_tags))
        results = library.by_tag(tag)
        ids = [s.scenario_id for s in results]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# ScenarioLibrary.list_domains
# ---------------------------------------------------------------------------


class TestScenarioLibraryListDomains:
    def test_list_domains_returns_sorted_list(self) -> None:
        library = ScenarioLibrary()
        domains = library.list_domains()
        assert domains == sorted(domains)

    def test_list_domains_has_four_built_in_domains(self) -> None:
        library = ScenarioLibrary()
        domains = library.list_domains()
        assert "healthcare" in domains
        assert "finance" in domains
        assert "legal" in domains
        assert "education" in domains

    def test_list_domains_unique_values(self) -> None:
        library = ScenarioLibrary()
        domains = library.list_domains()
        assert len(domains) == len(set(domains))


# ---------------------------------------------------------------------------
# ScenarioLibrary.__len__
# ---------------------------------------------------------------------------


class TestScenarioLibraryLen:
    def test_len_returns_40(self) -> None:
        library = ScenarioLibrary()
        assert len(library) == 40


# ---------------------------------------------------------------------------
# RiskTier comparison — NotImplemented branches in __le__ and __ge__
# ---------------------------------------------------------------------------


class TestRiskTierComparisonNotImplemented:
    def test_le_with_non_risk_tier_returns_not_implemented(self) -> None:
        result = RiskTier.ADVISORY.__le__("not_a_tier")
        assert result is NotImplemented

    def test_ge_with_non_risk_tier_returns_not_implemented(self) -> None:
        result = RiskTier.ADVISORY.__ge__("not_a_tier")
        assert result is NotImplemented

    def test_le_with_int_returns_not_implemented(self) -> None:
        result = RiskTier.INFORMATIONAL.__le__(0)
        assert result is NotImplemented

    def test_ge_with_int_returns_not_implemented(self) -> None:
        result = RiskTier.INFORMATIONAL.__ge__(0)
        assert result is NotImplemented

    def test_le_valid_comparison_works(self) -> None:
        assert RiskTier.INFORMATIONAL <= RiskTier.ADVISORY
        assert RiskTier.ADVISORY <= RiskTier.DECISION_SUPPORT
        assert RiskTier.ADVISORY <= RiskTier.ADVISORY  # equal

    def test_ge_valid_comparison_works(self) -> None:
        assert RiskTier.DECISION_SUPPORT >= RiskTier.ADVISORY
        assert RiskTier.ADVISORY >= RiskTier.INFORMATIONAL
        assert RiskTier.ADVISORY >= RiskTier.ADVISORY  # equal


# ---------------------------------------------------------------------------
# CertificationReporter.as_text — medium and low failure branches (lines 163, 165)
# ---------------------------------------------------------------------------


def _make_check(
    check_id: str,
    passed: bool,
    severity: FindingSeverity,
    name: str = "Test Check",
    description: str = "A test check.",
    detail: str = "",
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        check_name=name,
        passed=passed,
        severity=severity,
        description=description,
        detail=detail,
    )


class TestCertificationReporterAsTextMediumLow:
    def _build_result_with_severities(
        self, *severities: FindingSeverity
    ) -> object:
        evaluator = CertificationEvaluator("healthcare", RiskTier.INFORMATIONAL)
        checks = [
            _make_check(f"c{i}", False, sev)
            for i, sev in enumerate(severities)
        ]
        return evaluator.evaluate(checks)

    def test_as_text_contains_medium_line_when_medium_failures(self) -> None:
        result = self._build_result_with_severities(FindingSeverity.MEDIUM)
        reporter = CertificationReporter(result)  # type: ignore[arg-type]
        text = reporter.as_text()
        assert "MEDIUM" in text

    def test_as_text_contains_low_line_when_low_failures(self) -> None:
        result = self._build_result_with_severities(FindingSeverity.LOW)
        reporter = CertificationReporter(result)  # type: ignore[arg-type]
        text = reporter.as_text()
        assert "LOW" in text

    def test_as_text_medium_not_present_when_no_medium_failures(self) -> None:
        result = self._build_result_with_severities(FindingSeverity.HIGH)
        reporter = CertificationReporter(result)  # type: ignore[arg-type]
        text = reporter.as_text()
        # "MEDIUM" should only appear in the check summary section if medium failures > 0
        # (It may appear in the findings line as severity label, but not the summary count)
        lines = text.split("\n")
        medium_summary_lines = [
            ln for ln in lines if ln.strip().startswith("MEDIUM") and ":" in ln
        ]
        assert len(medium_summary_lines) == 0

    def test_as_text_all_severities_present(self) -> None:
        result = self._build_result_with_severities(
            FindingSeverity.CRITICAL,
            FindingSeverity.HIGH,
            FindingSeverity.MEDIUM,
            FindingSeverity.LOW,
        )
        reporter = CertificationReporter(result)  # type: ignore[arg-type]
        text = reporter.as_text()
        assert "CRITICAL" in text
        assert "HIGH" in text
        assert "MEDIUM" in text
        assert "LOW" in text

    def test_as_text_returns_string(self) -> None:
        result = self._build_result_with_severities(FindingSeverity.HIGH)
        reporter = CertificationReporter(result)  # type: ignore[arg-type]
        assert isinstance(reporter.as_text(), str)

    def test_as_text_no_failures_omits_failed_findings_section(self) -> None:
        evaluator = CertificationEvaluator("healthcare", RiskTier.INFORMATIONAL)
        result = evaluator.evaluate([_make_check("c1", True, FindingSeverity.HIGH)])
        reporter = CertificationReporter(result)
        text = reporter.as_text()
        assert "FAILED FINDINGS" not in text


# ---------------------------------------------------------------------------
# CitationGenerator.annotate_response — continue branch (line 159)
# ---------------------------------------------------------------------------


def _make_reference(
    claim: str,
    source_id: str,
    source_title: str = "Test Source",
    confidence: float = 0.9,
    excerpt: str = "",
) -> SourceReference:
    return SourceReference(
        claim=claim,
        source_id=source_id,
        source_title=source_title,
        confidence=confidence,
        excerpt=excerpt,
    )


class TestCitationGeneratorAnnotateResponseContinueBranch:
    def test_reference_with_unknown_source_id_is_skipped(self) -> None:
        """When a reference has a source_id not in citation_map, the continue branch is hit."""
        # Build a generator with one reference, then manually add a second reference
        # that has a source_id not in the generator's citation_map.
        ref1 = _make_reference("Aspirin inhibits COX enzymes.", "src-001", "Pharmacology Text")
        generator = CitationGenerator([ref1])

        # Directly manipulate _references to include an orphan source_id
        orphan_ref = _make_reference("This claim has no source.", "orphan-src-999")

        # Rebuild with orphan reference added after building citations
        # The generator only builds citations for refs passed to __init__,
        # so orphan_ref's source_id will NOT be in _citation_map.
        generator._references = [ref1, orphan_ref]  # type: ignore[attr-defined]

        response = "Aspirin inhibits COX enzymes. This claim has no source."
        annotated = generator.annotate_response(response)
        # The result should still be a string (not crash on the missing source_id)
        assert isinstance(annotated, str)
        # The ref1 claim should be annotated with [1]
        assert "[1]" in annotated
        # The orphan claim should not get annotated (continue branch was hit)
        assert "[2]" not in annotated

    def test_annotate_response_empty_response_returns_empty(self) -> None:
        ref = _make_reference("Some claim.", "src-001")
        generator = CitationGenerator([ref])
        assert generator.annotate_response("") == ""

    def test_annotate_response_no_references_returns_unchanged(self) -> None:
        generator = CitationGenerator([])
        response = "Some response with no citations."
        assert generator.annotate_response(response) == response

    def test_annotate_response_adds_markers_for_matching_claims(self) -> None:
        ref = _make_reference("Aspirin inhibits COX enzymes.", "src-001", "Pharmacology Text")
        generator = CitationGenerator([ref])
        response = "Aspirin inhibits COX enzymes."
        annotated = generator.annotate_response(response)
        assert "[1]" in annotated
