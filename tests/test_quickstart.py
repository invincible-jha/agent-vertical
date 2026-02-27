"""Test that the 3-line quickstart API works for agent-vertical."""
from __future__ import annotations


def test_quickstart_import() -> None:
    from agent_vertical import Template

    template = Template("healthcare")
    assert template is not None


def test_quickstart_domain_accessible() -> None:
    from agent_vertical import Template

    template = Template("finance")
    assert template.domain == "finance"


def test_quickstart_system_prompt() -> None:
    from agent_vertical import Template

    template = Template("healthcare")
    prompt = template.system_prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_quickstart_unknown_domain_graceful() -> None:
    from agent_vertical import Template

    template = Template("nonexistent-domain-xyz")
    # Should not raise — graceful fallback
    assert template.found is False
    assert "nonexistent-domain-xyz" in template.system_prompt


def test_quickstart_check_compliance() -> None:
    from agent_vertical import Template

    template = Template("healthcare")
    result = template.check_compliance("This is not medical advice.")
    assert result is not None
    assert hasattr(result, "passed")


def test_quickstart_repr() -> None:
    from agent_vertical import Template

    template = Template("legal")
    text = repr(template)
    assert "Template" in text
    assert "legal" in text
