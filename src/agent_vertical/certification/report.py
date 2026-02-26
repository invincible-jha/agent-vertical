"""Certification reporter — generate certification reports in JSON, text, and HTML."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from agent_vertical.certification.evaluator import CertificationResult
from agent_vertical.certification.scorer import FindingSeverity


_SEVERITY_COLOR: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "#dc2626",
    FindingSeverity.HIGH: "#ea580c",
    FindingSeverity.MEDIUM: "#ca8a04",
    FindingSeverity.LOW: "#2563eb",
    FindingSeverity.INFO: "#6b7280",
}

_SEVERITY_BADGE: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "CRITICAL",
    FindingSeverity.HIGH: "HIGH",
    FindingSeverity.MEDIUM: "MEDIUM",
    FindingSeverity.LOW: "LOW",
    FindingSeverity.INFO: "INFO",
}

ReportFormat = Literal["json", "text", "html"]


class CertificationReporter:
    """Generate human-readable certification reports from a :class:`CertificationResult`.

    Parameters
    ----------
    result:
        The :class:`CertificationResult` to report on.
    agent_name:
        Optional human-readable name for the agent being certified.
    report_version:
        Version string for the report format itself.

    Example
    -------
    ::

        reporter = CertificationReporter(result, agent_name="ClinicalAdvisor v2")
        print(reporter.as_text())
        with open("report.json", "w") as f:
            f.write(reporter.as_json(indent=2))
    """

    def __init__(
        self,
        result: CertificationResult,
        agent_name: str = "Agent Under Evaluation",
        report_version: str = "1.0",
    ) -> None:
        self._result = result
        self._agent_name = agent_name
        self._report_version = report_version
        self._generated_at = datetime.now(tz=timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def as_json(self, indent: int = 2) -> str:
        """Serialise the certification result to a JSON string.

        Parameters
        ----------
        indent:
            JSON indentation level.

        Returns
        -------
        str
            Pretty-printed JSON certification report.
        """
        payload = self._build_dict()
        return json.dumps(payload, indent=indent, ensure_ascii=False)

    def _build_dict(self) -> dict[str, object]:
        result = self._result
        sd = result.scoring_detail
        return {
            "report_version": self._report_version,
            "generated_at": self._generated_at,
            "agent_name": self._agent_name,
            "domain": result.domain,
            "risk_tier": result.tier.value,
            "score": result.score,
            "minimum_passing_score": result.tier.minimum_passing_score,
            "passed": result.passed,
            "summary": {
                "total_checks": sd.total_checks,
                "passed_checks": sd.passed_checks,
                "failed_checks": sd.failed_checks,
                "critical_failures": sd.critical_failures,
                "high_failures": sd.high_failures,
                "medium_failures": sd.medium_failures,
                "low_failures": sd.low_failures,
                "penalty_breakdown": sd.penalty_breakdown,
            },
            "findings": [
                {
                    "check_id": f.check_id,
                    "severity": f.severity.value,
                    "message": f.message,
                    "remediation": f.remediation,
                }
                for f in result.findings
            ],
            "critical_findings": [
                {
                    "check_id": f.check_id,
                    "message": f.message,
                    "remediation": f.remediation,
                }
                for f in result.critical_findings
            ],
        }

    # ------------------------------------------------------------------
    # Plain text
    # ------------------------------------------------------------------

    def as_text(self) -> str:
        """Generate a plain-text certification report.

        Returns
        -------
        str
            Human-readable text report.
        """
        result = self._result
        sd = result.scoring_detail
        lines: list[str] = []

        lines.append("=" * 72)
        lines.append("AGENT CERTIFICATION REPORT")
        lines.append("=" * 72)
        lines.append(f"Agent      : {self._agent_name}")
        lines.append(f"Domain     : {result.domain}")
        lines.append(f"Risk Tier  : {result.tier.value}")
        lines.append(f"Generated  : {self._generated_at}")
        lines.append("-" * 72)
        lines.append(f"Score      : {result.score} / 100")
        lines.append(f"Min. Score : {result.tier.minimum_passing_score}")
        verdict = "PASSED" if result.passed else "FAILED"
        lines.append(f"Verdict    : {verdict}")
        lines.append("-" * 72)
        lines.append("CHECK SUMMARY")
        lines.append(f"  Total checks  : {sd.total_checks}")
        lines.append(f"  Passed        : {sd.passed_checks}")
        lines.append(f"  Failed        : {sd.failed_checks}")
        if sd.critical_failures:
            lines.append(f"  CRITICAL      : {sd.critical_failures}")
        if sd.high_failures:
            lines.append(f"  HIGH          : {sd.high_failures}")
        if sd.medium_failures:
            lines.append(f"  MEDIUM        : {sd.medium_failures}")
        if sd.low_failures:
            lines.append(f"  LOW           : {sd.low_failures}")

        if result.failed_findings:
            lines.append("-" * 72)
            lines.append("FAILED FINDINGS")
            for finding in result.failed_findings:
                lines.append(f"\n  [{finding.severity.value}] {finding.check_id}")
                lines.append(f"    {finding.message}")
                if finding.remediation:
                    lines.append(f"    Remediation: {finding.remediation}")

        lines.append("=" * 72)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # HTML
    # ------------------------------------------------------------------

    def as_html(self) -> str:
        """Generate an HTML certification report.

        Returns
        -------
        str
            Self-contained HTML document.
        """
        result = self._result
        sd = result.scoring_detail
        verdict_color = "#16a34a" if result.passed else "#dc2626"
        verdict_label = "PASSED" if result.passed else "FAILED"

        findings_rows: list[str] = []
        for finding in result.failed_findings:
            color = _SEVERITY_COLOR.get(finding.severity, "#6b7280")
            badge = _SEVERITY_BADGE.get(finding.severity, finding.severity.value)
            findings_rows.append(
                f'<tr>'
                f'<td><span style="background:{color};color:white;padding:2px 6px;'
                f'border-radius:3px;font-size:0.75em">{badge}</span></td>'
                f'<td style="font-family:monospace;font-size:0.85em">{_escape(finding.check_id)}</td>'
                f'<td>{_escape(finding.message)}</td>'
                f'<td style="font-size:0.85em;color:#374151">{_escape(finding.remediation)}</td>'
                f'</tr>'
            )
        findings_html = "".join(findings_rows) if findings_rows else (
            '<tr><td colspan="4" style="text-align:center;color:#6b7280">'
            "No failed findings</td></tr>"
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Certification Report — {_escape(self._agent_name)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0; padding: 2rem; background: #f9fafb; color: #111827; }}
  .card {{ background: white; border-radius: 8px; padding: 2rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.12); margin-bottom: 1.5rem; }}
  h1 {{ margin: 0 0 0.5rem; font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 1.5rem; border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0.4rem; }}
  .meta {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem; }}
  .score-box {{ display: inline-block; font-size: 3rem; font-weight: 700;
                color: {verdict_color}; }}
  .verdict {{ display: inline-block; background: {verdict_color}; color: white;
              padding: 4px 14px; border-radius: 20px; font-weight: 600;
              font-size: 0.95rem; margin-left: 1rem; vertical-align: middle; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f3f4f6; font-weight: 600; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 1rem; margin-top: 1rem; }}
  .stat {{ background: #f3f4f6; border-radius: 6px; padding: 0.75rem 1rem; }}
  .stat-value {{ font-size: 1.5rem; font-weight: 700; }}
  .stat-label {{ font-size: 0.75rem; color: #6b7280; }}
</style>
</head>
<body>
<div class="card">
  <h1>Agent Certification Report</h1>
  <div class="meta">
    Agent: <strong>{_escape(self._agent_name)}</strong> &nbsp;|&nbsp;
    Domain: <strong>{_escape(result.domain)}</strong> &nbsp;|&nbsp;
    Risk Tier: <strong>{result.tier.value}</strong> &nbsp;|&nbsp;
    Generated: {_escape(self._generated_at)}
  </div>
  <div>
    <span class="score-box">{result.score}</span><span style="font-size:1.2rem;color:#6b7280">/100</span>
    <span class="verdict">{verdict_label}</span>
    <span style="margin-left:1rem;color:#6b7280;font-size:0.9rem">
      (minimum: {result.tier.minimum_passing_score})
    </span>
  </div>

  <h2>Summary</h2>
  <div class="stat-grid">
    <div class="stat"><div class="stat-value">{sd.total_checks}</div><div class="stat-label">Total Checks</div></div>
    <div class="stat"><div class="stat-value" style="color:#16a34a">{sd.passed_checks}</div><div class="stat-label">Passed</div></div>
    <div class="stat"><div class="stat-value" style="color:#dc2626">{sd.failed_checks}</div><div class="stat-label">Failed</div></div>
    <div class="stat"><div class="stat-value" style="color:#dc2626">{sd.critical_failures}</div><div class="stat-label">Critical</div></div>
    <div class="stat"><div class="stat-value" style="color:#ea580c">{sd.high_failures}</div><div class="stat-label">High</div></div>
    <div class="stat"><div class="stat-value" style="color:#ca8a04">{sd.medium_failures}</div><div class="stat-label">Medium</div></div>
  </div>
</div>

<div class="card">
  <h2>Failed Findings</h2>
  <table>
    <thead>
      <tr><th>Severity</th><th>Check ID</th><th>Message</th><th>Remediation</th></tr>
    </thead>
    <tbody>
      {findings_html}
    </tbody>
  </table>
</div>
</body>
</html>"""


def _escape(text: str) -> str:
    """Minimal HTML escaping for report values."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
