"""Template validator — structural and compliance coverage checking.

:class:`TemplateValidator` performs thorough static analysis of a
:class:`~agent_vertical.certified.schema.DomainTemplate`, returning a
:class:`ValidationResult` that separates hard errors from warnings and
groups compliance gaps by framework.

Classes
-------
ValidationResult
    Frozen dataclass holding the full outcome of a validation run.
TemplateValidator
    Validates templates for structural integrity, regex correctness, and
    compliance framework coverage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_vertical.certified.schema import (
    ComplianceFramework,
    DomainTemplate,
    EvalBenchmark,
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a :class:`TemplateValidator` run.

    Attributes
    ----------
    valid:
        ``True`` if no *errors* were found (warnings are allowed).
    errors:
        Hard errors that must be resolved before the template can be used.
    warnings:
        Non-blocking issues — templates with only warnings are still valid.
    compliance_gaps:
        Mapping of framework name (e.g. ``"HIPAA"``) to a list of missing
        or insufficient elements identified for that framework.
    """

    valid: bool
    errors: list[str]
    warnings: list[str]
    compliance_gaps: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Compliance coverage requirements per framework
# ---------------------------------------------------------------------------

# Each entry maps a framework to a list of (key, description) checks.
# "key" is a short label used internally; description is the human-readable
# gap message when the check fails.

_HIPAA_REQUIRED_RULE_PATTERNS: list[tuple[str, str]] = [
    ("phi_pattern", "No PHI detection pattern (e.g. SSN regex) found in safety rules."),
    ("disclaimer_pattern", "No 'not medical advice' disclaimer rule found in safety rules."),
    ("no_diagnosis", "No rule prohibiting diagnostic statements found in safety rules."),
]

_HIPAA_REQUIRED_TOOLS: list[tuple[str, str]] = [
    ("audit_logger", "Required tool 'audit_logger' is missing for HIPAA audit trail."),
    ("phi_detector", "Required tool 'phi_detector' is missing for PHI detection."),
]

_SOX_REQUIRED_RULE_PATTERNS: list[tuple[str, str]] = [
    ("no_buy_rec", "No rule prohibiting buy/sell recommendations found."),
    ("disclaimer_pattern", "No 'not investment advice' disclaimer rule found."),
    ("anti_fraud", "No anti-fraud detection pattern found in safety rules."),
]

_SOX_REQUIRED_TOOLS: list[tuple[str, str]] = [
    ("transaction_audit_trail", "Required tool 'transaction_audit_trail' is missing for SOX."),
    ("fraud_signal_detector", "Required tool 'fraud_signal_detector' is missing for SOX."),
]

_GDPR_REQUIRED_RULE_PATTERNS: list[tuple[str, str]] = [
    ("pii_pattern", "No PII detection/redaction rule found in safety rules."),
]

_GDPR_REQUIRED_TOOLS: list[tuple[str, str]] = [
    ("pii_redactor", "Required tool 'pii_redactor' is missing for GDPR data-minimisation."),
]

_SOC2_REQUIRED_TOOLS: list[tuple[str, str]] = [
    ("audit_logger", "Tool providing audit logging is missing for SOC2 availability/confidentiality."),
]

_STANDARD_BENCHMARK_NAMES: list[str] = [
    "precision",
    "recall",
    "f1_score",
    "pass_rate",
    "coverage",
    "accuracy",
    "calibration_error",
    "false_positive_rate",
    "sentiment_score",
]

_SEVERITY_VALID: frozenset[str] = frozenset({"warning", "error", "critical"})


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class TemplateValidator:
    """Validates :class:`~agent_vertical.certified.schema.DomainTemplate` instances.

    Usage
    -----
    ::

        validator = TemplateValidator()
        result = validator.validate(template)
        if not result.valid:
            for error in result.errors:
                print("ERROR:", error)

    All three public check methods can also be called independently.
    """

    def validate(self, template: DomainTemplate) -> ValidationResult:
        """Run a full validation pass on ``template``.

        Combines structural checks, safety-rule regex compilation, eval
        benchmark completeness, and per-framework compliance coverage.

        Parameters
        ----------
        template:
            The template to validate.

        Returns
        -------
        ValidationResult
            Aggregated result with errors, warnings, and compliance gaps.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- Structural checks ---
        if not template.metadata.name.strip():
            errors.append("metadata.name must not be empty.")

        if not template.metadata.domain.strip():
            errors.append("metadata.domain must not be empty.")

        if not template.metadata.description.strip():
            errors.append("metadata.description must not be empty.")

        if not template.system_prompt.strip():
            errors.append("system_prompt must not be empty.")
        elif len(template.system_prompt.strip()) < 50:
            warnings.append("system_prompt is very short (< 50 characters).")

        if not template.tool_configs:
            warnings.append("No tool configurations defined.")

        if not template.safety_rules:
            errors.append("No safety rules defined — at least one is required.")

        if not template.eval_benchmarks:
            warnings.append("No evaluation benchmarks defined.")

        if not template.compliance_evidence:
            warnings.append("No compliance evidence stubs provided.")

        # --- Safety rule checks ---
        safety_errors = self.check_safety_rules(template)
        errors.extend(safety_errors)

        # Severity validation
        for rule in template.safety_rules:
            if rule.severity not in _SEVERITY_VALID:
                errors.append(
                    f"Safety rule '{rule.rule_id}' has unrecognised severity "
                    f"'{rule.severity}'. Allowed values: {sorted(_SEVERITY_VALID)}."
                )

        # --- Eval benchmark checks ---
        benchmark_warnings = self.check_eval_completeness(template)
        warnings.extend(benchmark_warnings)

        # Threshold range validation
        for benchmark in template.eval_benchmarks:
            if not 0.0 <= benchmark.threshold <= 1.0:
                errors.append(
                    f"Benchmark '{benchmark.name}' threshold {benchmark.threshold} "
                    "is outside valid range [0.0, 1.0]."
                )

        # --- Compliance coverage ---
        compliance_gaps: dict[str, list[str]] = {}
        for framework in template.metadata.compliance_frameworks:
            if framework == ComplianceFramework.NONE:
                continue
            coverage_result = self.check_compliance_coverage(template, framework)
            raw_value = coverage_result.get(framework.value)
            if isinstance(raw_value, list) and raw_value:
                compliance_gaps[framework.value] = raw_value

        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            compliance_gaps=compliance_gaps,
        )

    def check_compliance_coverage(
        self, template: DomainTemplate, framework: ComplianceFramework
    ) -> dict[str, bool | list[str]]:
        """Check whether a template satisfies the required elements for ``framework``.

        Returns a dict keyed by the framework name.  The value is either:

        - ``True`` if coverage is complete.
        - A ``list[str]`` of gap descriptions if coverage is incomplete.

        Parameters
        ----------
        template:
            The template to check.
        framework:
            The compliance framework to check against.

        Returns
        -------
        dict[str, bool | list[str]]
        """
        key = framework.value
        if framework == ComplianceFramework.HIPAA:
            gaps = self._check_hipaa(template)
        elif framework == ComplianceFramework.SOX:
            gaps = self._check_sox(template)
        elif framework == ComplianceFramework.GDPR:
            gaps = self._check_gdpr(template)
        elif framework == ComplianceFramework.SOC2:
            gaps = self._check_soc2(template)
        elif framework == ComplianceFramework.PCI_DSS:
            gaps = self._check_pci_dss(template)
        else:
            return {key: True}

        if gaps:
            return {key: gaps}
        return {key: True}

    def check_safety_rules(self, template: DomainTemplate) -> list[str]:
        """Validate that all safety rule ``check_pattern`` fields compile as valid regex.

        Parameters
        ----------
        template:
            The template whose rules to validate.

        Returns
        -------
        list[str]
            One error string per rule whose pattern fails to compile.
            Empty list if all patterns are valid.
        """
        errors: list[str] = []
        for rule in template.safety_rules:
            try:
                re.compile(rule.check_pattern)
            except re.error as exc:
                errors.append(
                    f"Safety rule '{rule.rule_id}' has invalid regex pattern "
                    f"'{rule.check_pattern}': {exc}"
                )
        return errors

    def check_eval_completeness(self, template: DomainTemplate) -> list[str]:
        """Warn about missing standard benchmark metric types.

        Checks that the template's benchmarks cover at least one metric from
        the standard set (precision, recall, pass_rate, coverage, etc.).

        Parameters
        ----------
        template:
            The template to check.

        Returns
        -------
        list[str]
            Warning strings for missing standard metrics.  Empty list means
            all standard types are represented.
        """
        warnings_list: list[str] = []

        if not template.eval_benchmarks:
            warnings_list.append("No evaluation benchmarks defined.")
            return warnings_list

        defined_metrics: set[str] = {b.metric for b in template.eval_benchmarks}

        # Warn if neither precision nor recall is present for content-heavy templates
        has_quality_metric = bool(
            defined_metrics & {"precision", "recall", "f1_score", "accuracy"}
        )
        has_coverage_metric = bool(defined_metrics & {"coverage", "pass_rate"})

        if not has_quality_metric:
            warnings_list.append(
                "No quality metric (precision, recall, f1_score, accuracy) defined "
                "in eval benchmarks."
            )

        if not has_coverage_metric:
            warnings_list.append(
                "No coverage/pass-rate metric (coverage, pass_rate) defined "
                "in eval benchmarks."
            )

        # Warn about benchmarks with threshold == 0.0 (likely placeholder)
        for benchmark in template.eval_benchmarks:
            if benchmark.threshold == 0.0:
                warnings_list.append(
                    f"Benchmark '{benchmark.name}' has threshold 0.0 — this may be a placeholder."
                )

        return warnings_list

    # ------------------------------------------------------------------
    # Private per-framework checks
    # ------------------------------------------------------------------

    def _tool_names(self, template: DomainTemplate) -> set[str]:
        return {t.name for t in template.tool_configs}

    def _rule_patterns_combined(self, template: DomainTemplate) -> str:
        """Return all safety rule patterns joined for substring searching."""
        return " ".join(r.check_pattern for r in template.safety_rules)

    def _rule_descriptions_combined(self, template: DomainTemplate) -> str:
        return " ".join(r.description.lower() for r in template.safety_rules)

    def _check_hipaa(self, template: DomainTemplate) -> list[str]:
        gaps: list[str] = []
        patterns_text = self._rule_patterns_combined(template).lower()
        descriptions_text = self._rule_descriptions_combined(template)
        tool_names = self._tool_names(template)

        # PHI detection pattern (SSN or similar PII regex)
        phi_indicators = ["\\d{3}-\\d{2}-\\d{4}", "phi", "ssn", "social_security"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in phi_indicators):
            gaps.append("No PHI detection pattern (e.g. SSN regex) found in safety rules.")

        # Disclaimer rule
        disclaimer_indicators = ["medical advice", "not medical", "constitute medical"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in disclaimer_indicators):
            gaps.append("No 'not medical advice' disclaimer rule found in safety rules.")

        # No-diagnosis rule
        diagnosis_indicators = ["diagnos", "you have", "you\\s+have"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in diagnosis_indicators):
            gaps.append("No rule prohibiting diagnostic statements found in safety rules.")

        # Required tools
        if not any(t in tool_names for t in ("audit_logger", "audit_trail")):
            gaps.append("Required audit logging tool is missing for HIPAA audit trail.")
        if not any(t in tool_names for t in ("phi_detector", "phi_scanner", "pii_redactor")):
            gaps.append("Required PHI detection/redaction tool is missing.")

        return gaps

    def _check_sox(self, template: DomainTemplate) -> list[str]:
        gaps: list[str] = []
        patterns_text = self._rule_patterns_combined(template).lower()
        descriptions_text = self._rule_descriptions_combined(template)
        tool_names = self._tool_names(template)

        # No buy/sell recommendation rule
        rec_indicators = ["buy", "sell", "recommendation", "purchase"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in rec_indicators):
            gaps.append("No rule prohibiting buy/sell recommendations found.")

        # Investment disclaimer rule
        disclaimer_indicators = ["investment advice", "not investment", "constitute investment"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in disclaimer_indicators):
            gaps.append("No 'not investment advice' disclaimer rule found.")

        # Anti-fraud rule
        fraud_indicators = ["fraud", "launder", "anti.fraud", "insider"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in fraud_indicators):
            gaps.append("No anti-fraud detection pattern found in safety rules.")

        # Required tools
        if not any(t in tool_names for t in ("transaction_audit_trail", "audit_trail", "audit_logger")):
            gaps.append("Required transaction audit tool is missing for SOX.")
        if not any(t in tool_names for t in ("fraud_signal_detector", "fraud_detector")):
            gaps.append("Required fraud detection tool is missing for SOX.")

        return gaps

    def _check_gdpr(self, template: DomainTemplate) -> list[str]:
        gaps: list[str] = []
        patterns_text = self._rule_patterns_combined(template).lower()
        descriptions_text = self._rule_descriptions_combined(template)
        tool_names = self._tool_names(template)

        # PII detection/redaction rule
        pii_indicators = ["pii", "personal data", "email", "phone", "gdpr"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in pii_indicators):
            gaps.append("No PII detection/redaction rule found in safety rules.")

        # PII redaction tool
        if not any(t in tool_names for t in ("pii_redactor", "pii_detector", "phi_detector")):
            gaps.append("Required PII redaction tool is missing for GDPR data-minimisation.")

        return gaps

    def _check_soc2(self, template: DomainTemplate) -> list[str]:
        gaps: list[str] = []
        tool_names = self._tool_names(template)

        audit_tools = {"audit_logger", "audit_trail", "transaction_audit_trail", "audit_decision_logger"}
        if not audit_tools & tool_names:
            gaps.append(
                "Tool providing audit logging is missing for SOC2 availability/confidentiality."
            )

        return gaps

    def _check_pci_dss(self, template: DomainTemplate) -> list[str]:
        gaps: list[str] = []
        patterns_text = self._rule_patterns_combined(template).lower()
        descriptions_text = self._rule_descriptions_combined(template)
        tool_names = self._tool_names(template)

        # Card data pattern
        card_indicators = ["card", "pan", "credit.card", "payment", "cvv", "cardholder"]
        if not any(ind in patterns_text or ind in descriptions_text for ind in card_indicators):
            gaps.append("No payment card data detection rule found for PCI DSS.")

        # Encryption or tokenisation tool
        enc_tools = {"tokeniser", "tokenizer", "card_tokeniser", "payment_vault", "encryption_service"}
        if not enc_tools & tool_names:
            gaps.append("No card-data tokenisation/encryption tool found for PCI DSS.")

        return gaps
