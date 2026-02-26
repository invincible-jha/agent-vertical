"""Disclaimer generator — produce domain-appropriate disclaimers for agent responses.

:class:`DisclaimerGenerator` returns the correct regulatory disclaimer for a
given domain so that disclaimers are applied consistently across all templates
and tools.
"""
from __future__ import annotations

from agent_vertical.certification.risk_tier import RiskTier

# ---------------------------------------------------------------------------
# Disclaimer text library
# ---------------------------------------------------------------------------

_DOMAIN_DISCLAIMERS: dict[str, dict[RiskTier, str]] = {
    "healthcare": {
        RiskTier.INFORMATIONAL: (
            "DISCLAIMER: This content is for informational purposes only and does not "
            "constitute medical advice, diagnosis, or treatment. Always consult a "
            "qualified healthcare provider for medical guidance."
        ),
        RiskTier.ADVISORY: (
            "DISCLAIMER: This output is AI-generated preliminary guidance and does not "
            "constitute medical advice. It must be reviewed and confirmed by a licensed "
            "clinician before any clinical decision is made. In a medical emergency, "
            "call emergency services immediately."
        ),
        RiskTier.DECISION_SUPPORT: (
            "DISCLAIMER: This AI-generated output is intended for use by qualified "
            "healthcare professionals only. It does not replace clinical judgment and "
            "must be reviewed by a licensed clinician before any patient care decision "
            "is made. Not for direct patient use. This tool does not provide a diagnosis "
            "or treatment recommendation."
        ),
    },
    "finance": {
        RiskTier.INFORMATIONAL: (
            "DISCLAIMER: This content is for informational purposes only and does not "
            "constitute investment advice, a solicitation, or an offer to buy or sell "
            "any security. Past performance does not guarantee future results."
        ),
        RiskTier.ADVISORY: (
            "DISCLAIMER: This analysis is for qualified investment professionals only "
            "and does not constitute personalised investment advice. All investment "
            "decisions must be made by a registered investment advisor based on "
            "individual client suitability. Past performance does not guarantee "
            "future results."
        ),
        RiskTier.DECISION_SUPPORT: (
            "DISCLAIMER: This AI-generated risk assessment must be reviewed and approved "
            "by a qualified human analyst before any credit, lending, or underwriting "
            "decision is made. This output does not constitute a final lending or "
            "investment decision. Comply with all applicable fair lending laws."
        ),
    },
    "legal": {
        RiskTier.INFORMATIONAL: (
            "DISCLAIMER: This content does not constitute legal advice and should not "
            "be relied upon as such. Laws vary by jurisdiction. Consult a qualified "
            "attorney licensed in the relevant jurisdiction for advice specific to "
            "your situation."
        ),
        RiskTier.ADVISORY: (
            "DISCLAIMER: This analysis is AI-assisted and does not constitute legal "
            "advice. All findings require review by a qualified attorney before any "
            "legal action is taken. Communications with this tool are not protected "
            "by attorney-client privilege. Laws vary by jurisdiction."
        ),
        RiskTier.DECISION_SUPPORT: (
            "DISCLAIMER: This AI-generated output does not constitute legal advice and "
            "must be reviewed by a licensed attorney before use in any legal proceeding "
            "or compliance programme. Attorney-client privilege does not apply. Laws "
            "vary by jurisdiction and change frequently."
        ),
    },
    "education": {
        RiskTier.INFORMATIONAL: (
            "NOTE: This AI-generated educational content is a draft for review. "
            "Verify accuracy with a qualified educator or authoritative reference "
            "before use in formal instruction."
        ),
        RiskTier.ADVISORY: (
            "NOTE: This AI-generated content is intended as a planning aid for "
            "qualified educators. All materials require professional educator review "
            "and institutional approval before being used with students."
        ),
        RiskTier.DECISION_SUPPORT: (
            "NOTE: This AI-generated assessment or curriculum material must be reviewed "
            "and approved by a qualified educator before administration. Ensure all "
            "materials comply with institutional policies, accessibility requirements, "
            "and applicable privacy laws (including COPPA for learners under 13)."
        ),
    },
}

_GENERIC_DISCLAIMERS: dict[RiskTier, str] = {
    RiskTier.INFORMATIONAL: (
        "DISCLAIMER: This AI-generated content is provided for informational purposes "
        "only. Verify important information with authoritative sources."
    ),
    RiskTier.ADVISORY: (
        "DISCLAIMER: This AI-generated output is advisory only and must be reviewed "
        "by a qualified human expert before being acted upon."
    ),
    RiskTier.DECISION_SUPPORT: (
        "DISCLAIMER: This AI-generated output feeds into an automated decision process "
        "and must be reviewed by a qualified human reviewer before any decision is "
        "finalised."
    ),
}


class DisclaimerGenerator:
    """Generate domain-appropriate disclaimers for agent responses.

    Parameters
    ----------
    domain:
        The domain identifier (e.g. ``"healthcare"``, ``"finance"``).
    risk_tier:
        The :class:`RiskTier` of the agent producing the response.

    Example
    -------
    ::

        generator = DisclaimerGenerator("healthcare", RiskTier.ADVISORY)
        print(generator.get_disclaimer())
    """

    def __init__(self, domain: str, risk_tier: RiskTier) -> None:
        self._domain = domain.lower().strip()
        self._risk_tier = risk_tier

    def get_disclaimer(self) -> str:
        """Return the disclaimer text for this domain and risk tier.

        Returns
        -------
        str
            The appropriate disclaimer string.
        """
        domain_map = _DOMAIN_DISCLAIMERS.get(self._domain)
        if domain_map is not None:
            return domain_map.get(self._risk_tier, _GENERIC_DISCLAIMERS[self._risk_tier])
        return _GENERIC_DISCLAIMERS[self._risk_tier]

    def append_to(self, response: str, separator: str = "\n\n") -> str:
        """Append the disclaimer to ``response`` and return the combined string.

        Parameters
        ----------
        response:
            The agent response text.
        separator:
            Text inserted between the response and the disclaimer.

        Returns
        -------
        str
            The response with the disclaimer appended.
        """
        disclaimer = self.get_disclaimer()
        return f"{response}{separator}{disclaimer}"

    @staticmethod
    def available_domains() -> list[str]:
        """Return the list of domains with built-in disclaimers.

        Returns
        -------
        list[str]
        """
        return sorted(_DOMAIN_DISCLAIMERS.keys())
