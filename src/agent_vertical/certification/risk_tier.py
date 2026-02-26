"""Risk tier classification for domain-specific agents.

Defines the three risk tiers that govern how strictly an agent is evaluated
and what safeguards are required before deployment.
"""
from __future__ import annotations

from enum import Enum


class RiskTier(str, Enum):
    """Risk tier for a domain-specific agent.

    Higher tiers require stricter evaluation, more extensive compliance checks,
    and mandatory human review steps before the agent may be deployed.

    INFORMATIONAL
        The agent provides general information with no direct real-world impact.
        Errors are inconvenient but not harmful.  Example: a FAQ bot.

    ADVISORY
        The agent's output influences decisions made by a human.  Errors may
        cause financial, health, or legal harm if acted upon without review.
        Example: a clinical decision support tool or a lending recommendation engine.

    DECISION_SUPPORT
        The agent's output is used directly in automated downstream decisions
        with minimal human review.  The highest tier; any error may have
        immediate, material real-world consequences.
        Example: an automated underwriting system or a medication dosing assistant.
    """

    INFORMATIONAL = "INFORMATIONAL"
    ADVISORY = "ADVISORY"
    DECISION_SUPPORT = "DECISION_SUPPORT"

    # ------------------------------------------------------------------
    # Comparison helpers
    # ------------------------------------------------------------------

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RiskTier):
            return NotImplemented
        return _TIER_ORDER[self] < _TIER_ORDER[other]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, RiskTier):
            return NotImplemented
        return _TIER_ORDER[self] <= _TIER_ORDER[other]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, RiskTier):
            return NotImplemented
        return _TIER_ORDER[self] > _TIER_ORDER[other]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, RiskTier):
            return NotImplemented
        return _TIER_ORDER[self] >= _TIER_ORDER[other]

    @property
    def minimum_passing_score(self) -> int:
        """Minimum certification score (0-100) required to pass at this tier."""
        return _MINIMUM_SCORE[self]

    @property
    def requires_human_review(self) -> bool:
        """Whether a mandatory human review gate is required before deployment."""
        return self >= RiskTier.ADVISORY

    @property
    def requires_audit_trail(self) -> bool:
        """Whether an immutable audit trail is required for all agent decisions."""
        return self >= RiskTier.ADVISORY

    @property
    def requires_explainability(self) -> bool:
        """Whether every agent recommendation must include an explanation."""
        return self >= RiskTier.DECISION_SUPPORT


_TIER_ORDER: dict[RiskTier, int] = {
    RiskTier.INFORMATIONAL: 0,
    RiskTier.ADVISORY: 1,
    RiskTier.DECISION_SUPPORT: 2,
}

_MINIMUM_SCORE: dict[RiskTier, int] = {
    RiskTier.INFORMATIONAL: 60,
    RiskTier.ADVISORY: 75,
    RiskTier.DECISION_SUPPORT: 90,
}

# ------------------------------------------------------------------
# Domain → default risk tier mapping
# ------------------------------------------------------------------

_DOMAIN_TIER_MAP: dict[str, RiskTier] = {
    # Healthcare
    "healthcare": RiskTier.DECISION_SUPPORT,
    "medical": RiskTier.DECISION_SUPPORT,
    "clinical": RiskTier.DECISION_SUPPORT,
    "pharmacy": RiskTier.DECISION_SUPPORT,
    "nursing": RiskTier.DECISION_SUPPORT,
    # Finance
    "finance": RiskTier.ADVISORY,
    "financial": RiskTier.ADVISORY,
    "banking": RiskTier.ADVISORY,
    "lending": RiskTier.ADVISORY,
    "underwriting": RiskTier.DECISION_SUPPORT,
    "insurance": RiskTier.ADVISORY,
    "investment": RiskTier.ADVISORY,
    # Legal
    "legal": RiskTier.ADVISORY,
    "law": RiskTier.ADVISORY,
    "compliance": RiskTier.ADVISORY,
    "regulatory": RiskTier.ADVISORY,
    # Education
    "education": RiskTier.ADVISORY,
    "learning": RiskTier.INFORMATIONAL,
    "tutoring": RiskTier.INFORMATIONAL,
    # General
    "customer_support": RiskTier.INFORMATIONAL,
    "faq": RiskTier.INFORMATIONAL,
    "knowledge_base": RiskTier.INFORMATIONAL,
}


def risk_tier_for_domain(domain: str) -> RiskTier:
    """Return the default :class:`RiskTier` for the given domain name.

    The look-up is case-insensitive.  If the domain is unknown, the function
    defaults to :attr:`RiskTier.ADVISORY` — a safe, conservative choice that
    requires human review without imposing the most restrictive controls.

    Parameters
    ----------
    domain:
        A domain identifier such as ``"healthcare"``, ``"finance"``,
        ``"legal"``, or ``"education"``.

    Returns
    -------
    RiskTier
        The recommended risk tier for the given domain.

    Examples
    --------
    >>> risk_tier_for_domain("healthcare")
    <RiskTier.DECISION_SUPPORT: 'DECISION_SUPPORT'>
    >>> risk_tier_for_domain("education")
    <RiskTier.ADVISORY: 'ADVISORY'>
    >>> risk_tier_for_domain("unknown")
    <RiskTier.ADVISORY: 'ADVISORY'>
    """
    return _DOMAIN_TIER_MAP.get(domain.lower().strip(), RiskTier.ADVISORY)
