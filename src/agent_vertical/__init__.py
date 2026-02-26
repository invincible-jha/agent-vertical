"""agent-vertical — Domain-specific agent templates for common enterprise use cases.

Public API
----------
The stable public surface is everything exported from this module.
Anything inside submodules not re-exported here is considered private
and may change without notice.

Example
-------
::

    import agent_vertical

    # Load all built-in templates
    agent_vertical.load_all_templates()
    registry = agent_vertical.get_default_registry()
    template = registry.get("clinical_documentation")

    # Run compliance check on a response
    checker = agent_vertical.DomainComplianceChecker("healthcare")
    result = checker.check("This does not constitute medical advice.")

    # Run benchmark scenarios
    def my_agent(user_input: str) -> str:
        return "Informational response."

    runner = agent_vertical.BenchmarkRunner(my_agent, agent_name="MyAgent v1")
    report = runner.run_domain("healthcare")
    print(report.summary_text())
"""
from __future__ import annotations

__version__: str = "0.1.0"

# ---------------------------------------------------------------------------
# Certification
# ---------------------------------------------------------------------------
from agent_vertical.certification.evaluator import CertificationEvaluator, CertificationResult
from agent_vertical.certification.report import CertificationReporter
from agent_vertical.certification.requirements import (
    CertificationRequirement,
    RequirementSet,
    get_requirements,
)
from agent_vertical.certification.risk_tier import RiskTier, risk_tier_for_domain
from agent_vertical.certification.scorer import (
    CertificationScorer,
    CheckResult,
    FindingSeverity,
    ScoringResult,
)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
from agent_vertical.templates.base import (
    DomainTemplate,
    TemplateNotFoundError,
    TemplateRegistry,
    get_default_registry,
    load_all_templates,
)

# ---------------------------------------------------------------------------
# Grounding
# ---------------------------------------------------------------------------
from agent_vertical.grounding.citation import Citation, CitationGenerator
from agent_vertical.grounding.claim_tracer import ClaimTrace, ClaimTracer
from agent_vertical.grounding.disclaimer import DisclaimerGenerator
from agent_vertical.grounding.knowledge_base import InMemoryKB, KnowledgeBase, KnowledgeEntry
from agent_vertical.grounding.source_tracker import SourceReference, SourceTracker
from agent_vertical.grounding.validator import GroundingResult, GroundingValidator, SentenceGrounding

# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------
from agent_vertical.compliance.checker import (
    ComplianceCheckResult,
    DomainComplianceChecker,
    RuleViolation,
)
from agent_vertical.compliance.domain_rules import (
    ComplianceRule,
    DomainComplianceRules,
    RuleType,
    get_domain_rules,
    list_supported_domains,
)

# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
from agent_vertical.benchmarks.evaluator import (
    BehaviourCheck,
    ScenarioEvaluator,
    ScenarioResult,
)
from agent_vertical.benchmarks.runner import (
    BenchmarkReport,
    BenchmarkRunner,
    DomainBenchmarkSummary,
)
from agent_vertical.benchmarks.scenarios import BenchmarkScenario, ScenarioLibrary

__all__ = [
    # Version
    "__version__",
    # Certification
    "CertificationEvaluator",
    "CertificationRequirement",
    "CertificationReporter",
    "CertificationResult",
    "CertificationScorer",
    "CheckResult",
    "FindingSeverity",
    "RequirementSet",
    "RiskTier",
    "ScoringResult",
    "get_requirements",
    "risk_tier_for_domain",
    # Templates
    "DomainTemplate",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "get_default_registry",
    "load_all_templates",
    # Grounding
    "Citation",
    "CitationGenerator",
    "ClaimTrace",
    "ClaimTracer",
    "DisclaimerGenerator",
    "GroundingResult",
    "GroundingValidator",
    "InMemoryKB",
    "KnowledgeBase",
    "KnowledgeEntry",
    "SentenceGrounding",
    "SourceReference",
    "SourceTracker",
    # Compliance
    "ComplianceCheckResult",
    "ComplianceRule",
    "DomainComplianceChecker",
    "DomainComplianceRules",
    "RuleType",
    "RuleViolation",
    "get_domain_rules",
    "list_supported_domains",
    # Benchmarks
    "BehaviourCheck",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BenchmarkScenario",
    "DomainBenchmarkSummary",
    "ScenarioEvaluator",
    "ScenarioLibrary",
    "ScenarioResult",
]
