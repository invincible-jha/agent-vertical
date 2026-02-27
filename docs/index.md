# agent-vertical

Domain-Specific Agent Templates — certified templates for healthcare, finance, customer service, and legal with built-in compliance controls.

[![CI](https://github.com/invincible-jha/agent-vertical/actions/workflows/ci.yaml/badge.svg)](https://github.com/invincible-jha/agent-vertical/actions/workflows/ci.yaml)
[![PyPI version](https://img.shields.io/pypi/v/agent-vertical.svg)](https://pypi.org/project/agent-vertical/)
[![Python versions](https://img.shields.io/pypi/pyversions/agent-vertical.svg)](https://pypi.org/project/agent-vertical/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

---

## Installation

```bash
pip install agent-vertical
```

Verify the installation:

```bash
agent-vertical version
```

---

## Quick Start

```python
import agent_vertical

# See examples/01_quickstart.py for a working example
```

---

## Key Features

- **DomainTemplate dataclass** bundles a system prompt, permitted tools, ordered safety rules, evaluation criteria, and a `RiskTier` classification into a single reusable unit registered in a `TemplateRegistry`
- **Four domain template libraries** — healthcare, finance, legal, and education — each with multiple named templates (e.g., `clinical_documentation`, `lending_recommendation`, `contract_review`)
- **Three-level RiskTier hierarchy** (INFORMATIONAL, ADVISORY, DECISION_SUPPORT) governs how strictly templates are evaluated and what certifications must pass before deployment
- **CertificationEvaluator** runs domain-specific requirements (accuracy thresholds, citation requirements, disclaimer presence, scope constraints) and produces a structured certification report
- **GroundingValidator** checks agent responses for source citations, tracks claims back to knowledge-base entries, and flags unsupported assertions
- **Domain compliance checker** maps responses against domain-specific regulatory rules (e.g., HIPAA for healthcare, FCA rules for finance) and flags potential violations
- **Benchmark runner** executes domain scenario suites against a template-configured agent and scores results against the template's declared evaluation criteria

---

## Links

- [GitHub Repository](https://github.com/invincible-jha/agent-vertical)
- [PyPI Package](https://pypi.org/project/agent-vertical/)
- [Architecture](architecture.md)
- [Changelog](https://github.com/invincible-jha/agent-vertical/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/invincible-jha/agent-vertical/blob/main/CONTRIBUTING.md)

---

> Part of the [AumOS](https://github.com/aumos-ai) open-source agent infrastructure portfolio.
