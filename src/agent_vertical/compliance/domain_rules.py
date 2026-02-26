"""Domain compliance rules — per-domain prohibited phrases and required disclaimers.

:class:`DomainComplianceRules` aggregates :class:`ComplianceRule` objects for
a domain.  Rules are used by :class:`~agent_vertical.compliance.checker.DomainComplianceChecker`
to validate agent responses at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RuleType(str, Enum):
    """The type of compliance rule."""

    PROHIBITED_PHRASE = "PROHIBITED_PHRASE"
    """A phrase or pattern that must not appear in agent output."""

    REQUIRED_DISCLAIMER = "REQUIRED_DISCLAIMER"
    """A phrase or pattern that must appear in agent output."""

    PROHIBITED_PATTERN = "PROHIBITED_PATTERN"
    """A regular expression pattern that must not match agent output."""

    REQUIRED_PATTERN = "REQUIRED_PATTERN"
    """A regular expression pattern that must match agent output."""


@dataclass(frozen=True)
class ComplianceRule:
    """A single compliance rule for an agent domain.

    Attributes
    ----------
    rule_id:
        Unique identifier in dot notation (e.g. ``"hipaa.no_diagnosis"``).
    rule_type:
        Whether this rule prohibits content or requires it.
    pattern:
        The phrase or regex pattern to test against the agent response.
    description:
        Human-readable description of what this rule enforces.
    severity:
        Impact level: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
    remediation:
        Suggested fix when this rule is violated.
    is_regex:
        When ``True``, ``pattern`` is treated as a regular expression.
        When ``False``, it is a case-insensitive literal substring.
    """

    rule_id: str
    rule_type: RuleType
    pattern: str
    description: str
    severity: str
    remediation: str = ""
    is_regex: bool = False


@dataclass
class DomainComplianceRules:
    """A collection of :class:`ComplianceRule` objects for a specific domain.

    Attributes
    ----------
    domain:
        Domain identifier (e.g. ``"healthcare"``).
    rules:
        Ordered list of rules to enforce.
    """

    domain: str
    rules: list[ComplianceRule] = field(default_factory=list)

    def prohibited_phrase_rules(self) -> list[ComplianceRule]:
        """Return all PROHIBITED_PHRASE and PROHIBITED_PATTERN rules."""
        return [
            r
            for r in self.rules
            if r.rule_type in (RuleType.PROHIBITED_PHRASE, RuleType.PROHIBITED_PATTERN)
        ]

    def required_disclaimer_rules(self) -> list[ComplianceRule]:
        """Return all REQUIRED_DISCLAIMER and REQUIRED_PATTERN rules."""
        return [
            r
            for r in self.rules
            if r.rule_type in (RuleType.REQUIRED_DISCLAIMER, RuleType.REQUIRED_PATTERN)
        ]

    def by_severity(self, severity: str) -> list[ComplianceRule]:
        """Return rules filtered by severity level."""
        return [r for r in self.rules if r.severity == severity]


# ---------------------------------------------------------------------------
# Built-in domain rule definitions
# ---------------------------------------------------------------------------

HEALTHCARE_RULES = DomainComplianceRules(
    domain="healthcare",
    rules=[
        # --- Prohibited phrases ---
        ComplianceRule(
            rule_id="hipaa.no_diagnosis",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you have",
            description="Agent must not diagnose the user with a condition.",
            severity="critical",
            remediation=(
                "Remove diagnostic statements. Describe symptoms in general terms "
                "and refer the user to a licensed clinician for diagnosis."
            ),
        ),
        ComplianceRule(
            rule_id="hipaa.no_diagnosis_2",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you are diagnosed",
            description="Agent must not state a diagnosis.",
            severity="critical",
            remediation="Replace with 'you may wish to be evaluated for' and refer to a clinician.",
        ),
        ComplianceRule(
            rule_id="hipaa.no_prescribe",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="take this medication",
            description="Agent must not instruct users to take specific medications.",
            severity="critical",
            remediation="Remove prescriptive language. Refer user to a licensed prescriber.",
        ),
        ComplianceRule(
            rule_id="hipaa.no_dosage_instruction",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="dosage is",
            description="Agent must not specify medication dosages.",
            severity="critical",
            remediation=(
                "Remove dosage instructions. State that dosing requires clinician guidance."
            ),
        ),
        ComplianceRule(
            rule_id="hipaa.no_guarantee",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="guaranteed to",
            description="Agent must not guarantee treatment outcomes.",
            severity="high",
            remediation="Replace guarantees with appropriately qualified statements.",
        ),
        # --- Required disclaimers ---
        ComplianceRule(
            rule_id="hipaa.require_not_medical_advice",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="does not constitute medical advice",
            description="Response must include a 'not medical advice' disclaimer.",
            severity="critical",
            remediation="Append: 'This information does not constitute medical advice.'",
        ),
        ComplianceRule(
            rule_id="hipaa.require_consult_clinician",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="consult",
            description="Response must recommend consulting a healthcare professional.",
            severity="high",
            remediation="Append: 'Please consult a qualified healthcare provider.'",
        ),
    ],
)

FINANCE_RULES = DomainComplianceRules(
    domain="finance",
    rules=[
        # --- Prohibited phrases ---
        ComplianceRule(
            rule_id="sec.no_buy_recommendation",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you should buy",
            description="Agent must not make specific buy recommendations.",
            severity="critical",
            remediation=(
                "Remove buy recommendations. Replace with general market information "
                "and refer to a registered investment advisor."
            ),
        ),
        ComplianceRule(
            rule_id="sec.no_sell_recommendation",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you should sell",
            description="Agent must not make specific sell recommendations.",
            severity="critical",
            remediation="Remove sell recommendations and refer to a registered investment advisor.",
        ),
        ComplianceRule(
            rule_id="sec.no_guaranteed_returns",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="guaranteed return",
            description="Agent must not guarantee investment returns.",
            severity="critical",
            remediation=(
                "Remove return guarantees. State that all investments carry risk "
                "and past performance does not guarantee future results."
            ),
        ),
        ComplianceRule(
            rule_id="sec.no_risk_free",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="risk-free",
            description="Agent must not represent investments as risk-free.",
            severity="high",
            remediation="Qualify 'risk-free' language; all investments carry some risk.",
        ),
        ComplianceRule(
            rule_id="sec.no_price_prediction",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="will reach",
            description="Agent must not make specific price target predictions.",
            severity="high",
            remediation=(
                "Replace price predictions with historically-grounded ranges and "
                "include uncertainty qualifiers."
            ),
        ),
        # --- Required disclaimers ---
        ComplianceRule(
            rule_id="sec.require_not_investment_advice",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="does not constitute investment advice",
            description="Response must include a 'not investment advice' disclaimer.",
            severity="critical",
            remediation="Append: 'This content does not constitute investment advice.'",
        ),
        ComplianceRule(
            rule_id="sec.require_past_performance",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="past performance",
            description="Response must include a past-performance disclaimer.",
            severity="high",
            remediation=(
                "Append: 'Past performance does not guarantee future results.'"
            ),
        ),
    ],
)

LEGAL_RULES = DomainComplianceRules(
    domain="legal",
    rules=[
        # --- Prohibited phrases ---
        ComplianceRule(
            rule_id="legal.no_you_will_win",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you will win",
            description="Agent must not predict litigation outcomes.",
            severity="critical",
            remediation="Remove outcome predictions. Note that litigation outcomes are uncertain.",
        ),
        ComplianceRule(
            rule_id="legal.no_you_should_sue",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="you should sue",
            description="Agent must not recommend specific legal actions.",
            severity="critical",
            remediation=(
                "Remove specific legal action recommendations. Refer user to a "
                "qualified attorney for advice on their situation."
            ),
        ),
        ComplianceRule(
            rule_id="legal.no_legal_advice",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="my legal advice is",
            description="Agent must not present output as legal advice.",
            severity="critical",
            remediation=(
                "Remove the phrase 'my legal advice is'. Replace with "
                "'for informational purposes' framing."
            ),
        ),
        ComplianceRule(
            rule_id="legal.no_guarantee_outcome",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="guaranteed outcome",
            description="Agent must not guarantee legal outcomes.",
            severity="high",
            remediation="Remove outcome guarantees; legal results are inherently uncertain.",
        ),
        # --- Required disclaimers ---
        ComplianceRule(
            rule_id="legal.require_not_legal_advice",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="does not constitute legal advice",
            description="Response must include a 'not legal advice' disclaimer.",
            severity="critical",
            remediation="Append: 'This content does not constitute legal advice.'",
        ),
        ComplianceRule(
            rule_id="legal.require_consult_attorney",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="consult",
            description="Response must recommend consulting a qualified attorney.",
            severity="high",
            remediation="Append: 'Please consult a qualified attorney for advice on your situation.'",
        ),
        ComplianceRule(
            rule_id="legal.require_jurisdiction_caveat",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="jurisdiction",
            description=(
                "Response referencing law must include a jurisdiction caveat."
            ),
            severity="medium",
            remediation="Note: 'Laws vary by jurisdiction; verify requirements in your location.'",
        ),
    ],
)

EDUCATION_RULES = DomainComplianceRules(
    domain="education",
    rules=[
        # --- Prohibited phrases ---
        ComplianceRule(
            rule_id="edu.no_complete_for_student",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="here is your essay",
            description="Agent must not write assignments for students to submit as their own.",
            severity="critical",
            remediation=(
                "Remove completed assignment text. Offer guidance, outlines, and "
                "feedback instead of complete work."
            ),
        ),
        ComplianceRule(
            rule_id="edu.no_pii_request",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="what is your home address",
            description="Agent must not request student PII.",
            severity="critical",
            remediation="Remove requests for personally identifiable information.",
        ),
        ComplianceRule(
            rule_id="edu.no_age_inappropriate",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="adult content",
            description="Agent must not produce age-inappropriate content.",
            severity="critical",
            remediation="Remove adult content and ensure all material is age-appropriate.",
        ),
        ComplianceRule(
            rule_id="edu.no_stereotype",
            rule_type=RuleType.PROHIBITED_PHRASE,
            pattern="girls are not good at",
            description="Agent must not produce stereotyping content.",
            severity="high",
            remediation="Remove stereotypes and replace with inclusive, evidence-based framing.",
        ),
        # --- Required disclaimers ---
        ComplianceRule(
            rule_id="edu.require_educator_review",
            rule_type=RuleType.REQUIRED_DISCLAIMER,
            pattern="educator review",
            description=(
                "Curriculum and assessment outputs must include an educator review notice."
            ),
            severity="medium",
            remediation=(
                "Append: 'This content is a draft and requires educator review before "
                "use with students.'"
            ),
        ),
    ],
)

# ---------------------------------------------------------------------------
# Registry of built-in domain rules
# ---------------------------------------------------------------------------

_DOMAIN_RULES_REGISTRY: dict[str, DomainComplianceRules] = {
    "healthcare": HEALTHCARE_RULES,
    "medical": HEALTHCARE_RULES,
    "clinical": HEALTHCARE_RULES,
    "finance": FINANCE_RULES,
    "financial": FINANCE_RULES,
    "banking": FINANCE_RULES,
    "investment": FINANCE_RULES,
    "legal": LEGAL_RULES,
    "law": LEGAL_RULES,
    "compliance": LEGAL_RULES,
    "education": EDUCATION_RULES,
    "learning": EDUCATION_RULES,
    "tutoring": EDUCATION_RULES,
}


def get_domain_rules(domain: str) -> DomainComplianceRules:
    """Return the :class:`DomainComplianceRules` for the given domain.

    Parameters
    ----------
    domain:
        Domain identifier (case-insensitive).  Unknown domains return an
        empty :class:`DomainComplianceRules`.

    Returns
    -------
    DomainComplianceRules
    """
    key = domain.lower().strip()
    return _DOMAIN_RULES_REGISTRY.get(key, DomainComplianceRules(domain=domain))


def list_supported_domains() -> list[str]:
    """Return a sorted list of unique supported domain names.

    Returns
    -------
    list[str]
    """
    return sorted({HEALTHCARE_RULES.domain, FINANCE_RULES.domain,
                   LEGAL_RULES.domain, EDUCATION_RULES.domain})
