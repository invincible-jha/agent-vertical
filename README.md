# agent-vertical

Domain-specific agent templates for common enterprise use cases

[![CI](https://github.com/aumos-ai/agent-vertical/actions/workflows/ci.yaml/badge.svg)](https://github.com/aumos-ai/agent-vertical/actions/workflows/ci.yaml)
[![PyPI version](https://img.shields.io/pypi/v/agent-vertical.svg)](https://pypi.org/project/agent-vertical/)
[![Python versions](https://img.shields.io/pypi/pyversions/agent-vertical.svg)](https://pypi.org/project/agent-vertical/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Part of the [AumOS](https://github.com/aumos-ai) open-source agent infrastructure portfolio.

---

## Features

- `DomainTemplate` dataclass bundles a system prompt, permitted tools, ordered safety rules, evaluation criteria, and a `RiskTier` classification into a single reusable unit registered in a `TemplateRegistry`
- Four domain template libraries — healthcare, finance, legal, and education — each with multiple named templates (e.g., `clinical_documentation`, `lending_recommendation`, `contract_review`)
- Three-level `RiskTier` hierarchy (INFORMATIONAL, ADVISORY, DECISION_SUPPORT) governs how strictly templates are evaluated and what certifications must pass before deployment
- `CertificationEvaluator` runs domain-specific requirements (accuracy thresholds, citation requirements, disclaimer presence, scope constraints) and produces a structured certification report
- `GroundingValidator` checks agent responses for source citations, tracks claims back to knowledge-base entries, and flags unsupported assertions
- Domain compliance checker maps responses against domain-specific regulatory rules (e.g., HIPAA for healthcare, FCA rules for finance) and flags potential violations
- Benchmark runner executes domain scenario suites against a template-configured agent and scores results against the template's declared evaluation criteria

## Current Limitations

> **Transparency note**: We list known limitations to help you evaluate fit.

- **Domains**: 4 domains (healthcare, finance, education, legal). Retail, logistics, HR, manufacturing pending.
- **Templates**: 12 templates total — limited coverage per domain.
- **Customization**: Template-based — no dynamic domain generation.

## Quick Start

Install from PyPI:

```bash
pip install agent-vertical
```

Verify the installation:

```bash
agent-vertical version
```

Basic usage:

```python
import agent_vertical

# See examples/01_quickstart.py for a working example
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Examples](examples/README.md)

## Enterprise Upgrade

For production deployments requiring SLA-backed support and advanced
integrations, contact the maintainers or see the commercial extensions documentation.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md)
before opening a pull request.

## License

Apache 2.0 — see [LICENSE](LICENSE) for full terms.

---

Part of [AumOS](https://github.com/aumos-ai) — open-source agent infrastructure.
