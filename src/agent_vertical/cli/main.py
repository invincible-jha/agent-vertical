"""CLI entry point for agent-vertical.

Invoked as::

    agent-vertical [OPTIONS] COMMAND [ARGS]...

or, during development::

    python -m agent_vertical.cli.main

Commands
--------
version
    Show detailed version information.
plugins
    List all registered plugins.
list-domains
    List all domains that have built-in templates.
list-templates
    List all registered templates, optionally filtered by domain.
generate
    Show a template's system prompt and configuration.
certify
    Run a certification evaluation for a domain and risk tier.
benchmark
    Run benchmark scenarios for a domain or all domains.
compliance-check
    Check a text response for domain compliance violations.
"""
from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """Domain-specific agent templates for common enterprise use cases"""


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@cli.command(name="version")
def version_command() -> None:
    """Show detailed version information."""
    from agent_vertical import __version__

    console.print(f"[bold]agent-vertical[/bold] v{__version__}")


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


@cli.command(name="plugins")
def plugins_command() -> None:
    """List all registered plugins loaded from entry-points."""
    console.print("[bold]Registered plugins:[/bold]")
    console.print("  (No plugins registered. Install a plugin package to see entries here.)")


# ---------------------------------------------------------------------------
# list-domains
# ---------------------------------------------------------------------------


@cli.command(name="list-domains")
def list_domains_command() -> None:
    """List all domains that have built-in templates."""
    from agent_vertical.templates.base import load_all_templates

    registry = load_all_templates()
    domains = registry.list_domains()

    if not domains:
        console.print("[yellow]No domains found.[/yellow]")
        return

    table = Table(title="Available Domains", show_header=True, header_style="bold cyan")
    table.add_column("Domain", style="bold")
    table.add_column("Templates", justify="right")
    table.add_column("Default Risk Tier")

    from agent_vertical.certification.risk_tier import risk_tier_for_domain

    for domain in domains:
        templates = registry.list_templates(domain=domain)
        tier = risk_tier_for_domain(domain)
        table.add_row(domain, str(len(templates)), tier.value)

    console.print(table)


# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------


@cli.command(name="list-templates")
@click.option(
    "--domain",
    "-d",
    default=None,
    help="Filter templates by domain (e.g. healthcare, finance, legal, education).",
)
def list_templates_command(domain: str | None) -> None:
    """List all registered templates, optionally filtered by domain."""
    from agent_vertical.templates.base import load_all_templates

    registry = load_all_templates()
    templates = registry.list_templates(domain=domain)

    if not templates:
        msg = f"No templates found for domain '{domain}'." if domain else "No templates found."
        console.print(f"[yellow]{msg}[/yellow]")
        return

    title = f"Templates — {domain}" if domain else "All Templates"
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Domain")
    table.add_column("Risk Tier")
    table.add_column("Description")

    for template in templates:
        description = template.description[:80] + "..." if len(template.description) > 80 else template.description
        table.add_row(
            template.name,
            template.domain,
            template.risk_tier.value,
            description,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@cli.command(name="generate")
@click.argument("template_name")
@click.option(
    "--show-prompt",
    is_flag=True,
    default=False,
    help="Include the full system prompt in the output.",
)
@click.option(
    "--show-rules",
    is_flag=True,
    default=False,
    help="Include safety rules and evaluation criteria.",
)
def generate_command(template_name: str, show_prompt: bool, show_rules: bool) -> None:
    """Show configuration for a specific template.

    TEMPLATE_NAME is the machine-readable name such as 'clinical_documentation'.
    """
    from agent_vertical.templates.base import TemplateNotFoundError, load_all_templates

    registry = load_all_templates()
    try:
        template = registry.get(template_name)
    except TemplateNotFoundError:
        available = [t.name for t in registry.list_templates()]
        console.print(f"[red]Template '{template_name}' not found.[/red]")
        console.print(f"Available templates: {', '.join(available)}")
        sys.exit(1)

    console.print(f"\n[bold cyan]Template:[/bold cyan] {template.name}")
    console.print(f"[bold]Domain:[/bold]      {template.domain}")
    console.print(f"[bold]Risk Tier:[/bold]   {template.risk_tier.value}")
    console.print(f"[bold]Description:[/bold] {template.description}")

    console.print(f"\n[bold]Tools ({len(template.tools)}):[/bold]")
    for tool in template.tools:
        console.print(f"  - {tool}")

    console.print(f"\n[bold]Required Certifications ({len(template.required_certifications)}):[/bold]")
    for cert in template.required_certifications:
        console.print(f"  - {cert}")

    if show_rules:
        console.print(f"\n[bold]Safety Rules ({len(template.safety_rules)}):[/bold]")
        for i, rule in enumerate(template.safety_rules, 1):
            console.print(f"  {i}. {rule}")

        console.print(f"\n[bold]Evaluation Criteria ({len(template.evaluation_criteria)}):[/bold]")
        for i, criterion in enumerate(template.evaluation_criteria, 1):
            console.print(f"  {i}. {criterion}")

    if show_prompt:
        console.print("\n[bold]System Prompt:[/bold]")
        console.print("-" * 60)
        console.print(template.system_prompt)
        console.print("-" * 60)


# ---------------------------------------------------------------------------
# certify
# ---------------------------------------------------------------------------


@cli.command(name="certify")
@click.argument("domain")
@click.option(
    "--tier",
    "-t",
    type=click.Choice(["INFORMATIONAL", "ADVISORY", "DECISION_SUPPORT"], case_sensitive=False),
    default=None,
    help="Risk tier override. Defaults to the domain's default tier.",
)
@click.option(
    "--agent-name",
    "-a",
    default=None,
    help="Human-readable agent name for the report.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format: text (default) or json.",
)
def certify_command(
    domain: str,
    tier: str | None,
    agent_name: str | None,
    output_format: str,
) -> None:
    """Run a certification requirements check for a domain and risk tier.

    DOMAIN is the domain to certify (e.g. healthcare, finance, legal, education).
    """
    from agent_vertical.certification.requirements import get_requirements
    from agent_vertical.certification.risk_tier import RiskTier, risk_tier_for_domain

    resolved_tier: RiskTier
    if tier is not None:
        resolved_tier = RiskTier(tier.upper())
    else:
        resolved_tier = risk_tier_for_domain(domain)

    requirement_set = get_requirements(domain, resolved_tier)
    resolved_agent_name = agent_name or f"{domain.title()} Agent"

    if output_format == "json":
        import json

        payload = {
            "agent_name": resolved_agent_name,
            "domain": domain,
            "risk_tier": resolved_tier.value,
            "minimum_passing_score": resolved_tier.minimum_passing_score,
            "requires_human_review": resolved_tier.requires_human_review,
            "requires_audit_trail": resolved_tier.requires_audit_trail,
            "requires_explainability": resolved_tier.requires_explainability,
            "mandatory_requirements": requirement_set.mandatory_count(),
            "critical_requirements": len(requirement_set.critical_requirements()),
            "requirements": [
                {
                    "id": r.requirement_id,
                    "name": r.name,
                    "severity": r.severity.value,
                    "description": r.description,
                    "rationale": r.rationale,
                }
                for r in requirement_set.requirements
            ],
        }
        console.print_json(json.dumps(payload, indent=2))
        return

    console.print(f"\n[bold cyan]Certification Requirements[/bold cyan]")
    console.print(f"Agent      : {resolved_agent_name}")
    console.print(f"Domain     : {domain}")
    console.print(f"Risk Tier  : {resolved_tier.value}")
    console.print(f"Min. Score : {resolved_tier.minimum_passing_score}")
    console.print(f"Human Review Required : {'Yes' if resolved_tier.requires_human_review else 'No'}")
    console.print(f"Audit Trail Required  : {'Yes' if resolved_tier.requires_audit_trail else 'No'}")
    console.print(f"Explainability Required: {'Yes' if resolved_tier.requires_explainability else 'No'}")

    console.print(f"\n[bold]Requirements ({requirement_set.mandatory_count()}):[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name")
    table.add_column("Severity")
    table.add_column("Description")

    severity_colors = {
        "CRITICAL": "red",
        "HIGH": "yellow",
        "MEDIUM": "cyan",
        "LOW": "blue",
        "INFO": "dim",
    }

    for req in requirement_set.requirements:
        color = severity_colors.get(req.severity.value, "white")
        table.add_row(
            req.requirement_id,
            req.name,
            f"[{color}]{req.severity.value}[/{color}]",
            req.description[:70] + ("..." if len(req.description) > 70 else ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------


@cli.command(name="benchmark")
@click.option(
    "--domain",
    "-d",
    default=None,
    help="Run scenarios for a specific domain only. Runs all domains if omitted.",
)
@click.option(
    "--difficulty",
    type=click.Choice(["easy", "medium", "hard"], case_sensitive=False),
    default=None,
    help="Filter scenarios by difficulty level.",
)
@click.option(
    "--agent-name",
    "-a",
    default="Demo Agent",
    help="Human-readable name for the agent under test.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format: text (default) or json.",
)
def benchmark_command(
    domain: str | None,
    difficulty: str | None,
    agent_name: str,
    output_format: str,
) -> None:
    """Run benchmark scenarios and display results.

    By default runs against a stub agent that always returns a compliant
    disclaimer response, useful for verifying the benchmark infrastructure.
    """
    from agent_vertical.benchmarks.runner import BenchmarkRunner
    from agent_vertical.benchmarks.scenarios import ScenarioLibrary

    library = ScenarioLibrary()

    # Stub agent for CLI demo purposes
    def _stub_agent(user_input: str) -> str:  # noqa: ARG001
        return (
            "This information is provided for general informational purposes only. "
            "It does not constitute medical, legal, or financial advice. "
            "Please consult a qualified professional. "
            "This does not constitute investment advice. "
            "Past performance does not guarantee future results. "
            "This does not constitute legal advice. "
            "Consult a qualified attorney. "
            "Jurisdiction and applicable laws vary. "
            "This output requires educator review before use with students."
        )

    runner = BenchmarkRunner(_stub_agent, agent_name=agent_name)

    if difficulty is not None:
        scenarios = library.by_difficulty(difficulty)
        if domain is not None:
            scenarios = [s for s in scenarios if s.domain == domain]
        report = runner.run_scenarios(scenarios)
    elif domain is not None:
        report = runner.run_domain(domain)
    else:
        report = runner.run_all()

    if output_format == "json":
        import json

        payload = {
            "run_id": report.run_id,
            "agent_name": report.agent_name,
            "total_scenarios": report.total_scenarios,
            "passed_scenarios": report.passed_scenarios,
            "failed_scenarios": report.failed_scenarios,
            "overall_pass_rate": report.overall_pass_rate,
            "overall_average_score": report.overall_average_score,
            "domain_summaries": [
                {
                    "domain": s.domain,
                    "total": s.total_scenarios,
                    "passed": s.passed_scenarios,
                    "pass_rate": s.pass_rate,
                    "average_score": s.average_score,
                    "by_difficulty": s.by_difficulty,
                }
                for s in sorted(report.domain_summaries, key=lambda s: s.domain)
            ],
            "failed_scenario_ids": sorted(report.failed_scenario_ids),
        }
        console.print_json(json.dumps(payload, indent=2))
        return

    console.print(report.summary_text())


# ---------------------------------------------------------------------------
# compliance-check
# ---------------------------------------------------------------------------


@cli.command(name="compliance-check")
@click.argument("domain")
@click.option(
    "--response",
    "-r",
    default=None,
    help="The agent response text to check. If omitted, reads from stdin.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format: text (default) or json.",
)
def compliance_check_command(
    domain: str,
    response: str | None,
    output_format: str,
) -> None:
    """Check an agent response for domain compliance violations.

    DOMAIN is the domain to check against (e.g. healthcare, finance, legal, education).

    Pass the response text via --response or pipe it via stdin.
    """
    from agent_vertical.compliance.checker import DomainComplianceChecker

    if response is None:
        if not sys.stdin.isatty():
            response = sys.stdin.read().strip()
        else:
            console.print(
                "[yellow]No response provided. Use --response or pipe text via stdin.[/yellow]"
            )
            sys.exit(1)

    checker = DomainComplianceChecker(domain)
    result = checker.check(response)

    if output_format == "json":
        import json

        payload = {
            "domain": result.domain,
            "is_compliant": result.is_compliant,
            "passed_rules": result.passed_rules,
            "total_rules": result.total_rules,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_type": v.rule_type.value,
                    "severity": v.severity,
                    "description": v.description,
                    "matched_text": v.matched_text,
                    "remediation": v.remediation,
                }
                for v in result.violations
            ],
        }
        console.print_json(json.dumps(payload, indent=2))
        return

    verdict_style = "green" if result.is_compliant else "red"
    verdict_label = "COMPLIANT" if result.is_compliant else "NON-COMPLIANT"

    console.print(f"\n[bold]Compliance Check — {domain}[/bold]")
    console.print(f"Verdict    : [{verdict_style}]{verdict_label}[/{verdict_style}]")
    console.print(f"Rules      : {result.passed_rules}/{result.total_rules} passed")
    console.print(f"Violations : {len(result.violations)} total, "
                  f"{len(result.critical_violations)} critical, "
                  f"{len(result.high_violations)} high")

    if result.violations:
        console.print("\n[bold]Violations:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Severity")
        table.add_column("Rule ID", style="dim")
        table.add_column("Description")
        table.add_column("Matched / Missing")

        severity_colors = {
            "critical": "red",
            "high": "yellow",
            "medium": "cyan",
            "low": "blue",
        }

        for violation in result.violations:
            color = severity_colors.get(violation.severity, "white")
            matched_label = (
                f'[dim]"{violation.matched_text[:40]}"[/dim]'
                if violation.matched_text
                else "[dim](missing required text)[/dim]"
            )
            table.add_row(
                f"[{color}]{violation.severity.upper()}[/{color}]",
                violation.rule_id,
                violation.description[:60] + ("..." if len(violation.description) > 60 else ""),
                matched_label,
            )
        console.print(table)

        console.print("\n[bold]Remediations:[/bold]")
        for violation in result.violations:
            if violation.remediation:
                console.print(f"  [{violation.rule_id}] {violation.remediation}")
    else:
        console.print("\n[green]No violations found.[/green]")


if __name__ == "__main__":
    cli()
