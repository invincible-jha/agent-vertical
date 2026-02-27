"""Certified template library — built-in templates and runtime registry.

This module provides :class:`TemplateLibrary`, a registry of
:class:`~agent_vertical.certified.schema.DomainTemplate` instances, and
defines five built-in templates covering common regulated domains.

Built-in Templates
------------------
healthcare_hipaa
    Patient data handling with HIPAA safeguards, PHI detection rules,
    and audit logging requirements.
finance_sox
    Financial data processing with SOX audit trails, anti-fraud detection,
    and segregation-of-duties governance.
customer_service
    Sentiment-aware customer interactions with PII redaction, escalation
    triggers, and satisfaction benchmarks.
content_moderation
    Content review with toxicity detection, bias monitoring, and
    age-appropriateness checks.
research_assistant
    Academic research support with citation verification, source attribution,
    and confidence calibration.

Usage
-----
::

    library = TemplateLibrary()
    template = library.get_template("healthcare_hipaa")
    library.export_template("healthcare_hipaa", "/tmp/healthcare.yaml")

    custom = DomainTemplate.from_yaml(open("my_template.yaml").read())
    library.register_custom(custom)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_vertical.certified.schema import (
    ComplianceFramework,
    DomainTemplate,
    EvalBenchmark,
    RiskLevel,
    SafetyRule,
    TemplateMetadata,
    ToolConfig,
)


# ---------------------------------------------------------------------------
# Helper to build TemplateMetadata concisely
# ---------------------------------------------------------------------------


def _meta(
    name: str,
    domain: str,
    description: str,
    frameworks: list[ComplianceFramework],
    risk_level: RiskLevel,
    tags: list[str],
    version: str = "1.0.0",
    author: str = "AumOS Contributors",
) -> TemplateMetadata:
    return TemplateMetadata(
        name=name,
        version=version,
        domain=domain,
        compliance_frameworks=frameworks,
        risk_level=risk_level,
        description=description,
        author=author,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Template 1 — Healthcare / HIPAA
# ---------------------------------------------------------------------------

_HEALTHCARE_SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        rule_id="hipaa.phi_pattern_detection",
        description="Detect and redact social security number patterns before output.",
        severity="critical",
        check_pattern=r"\b\d{3}-\d{2}-\d{4}\b",
    ),
    SafetyRule(
        rule_id="hipaa.no_diagnosis_statement",
        description="Agent must not assert a diagnosis with 'you have [condition]' phrasing.",
        severity="critical",
        check_pattern=r"\byou\s+have\s+\w+",
    ),
    SafetyRule(
        rule_id="hipaa.no_prescribing",
        description="Agent must not issue prescribing instructions.",
        severity="critical",
        check_pattern=r"\btake\s+(this\s+)?medication\b",
    ),
    SafetyRule(
        rule_id="hipaa.require_medical_advice_disclaimer",
        description="Response must contain a 'not medical advice' disclaimer.",
        severity="error",
        check_pattern=r"(not\s+medical\s+advice|does\s+not\s+constitute\s+medical\s+advice)",
    ),
    SafetyRule(
        rule_id="hipaa.require_clinician_referral",
        description="Response must recommend consulting a licensed healthcare provider.",
        severity="error",
        check_pattern=r"(consult|speak\s+with|contact)\s+(a\s+)?(licensed\s+)?(clinician|physician|doctor|healthcare\s+provider)",
    ),
    SafetyRule(
        rule_id="hipaa.no_guaranteed_outcome",
        description="Agent must not guarantee treatment outcomes.",
        severity="error",
        check_pattern=r"\bguaranteed?\s+to\b",
    ),
    SafetyRule(
        rule_id="hipaa.minimum_consent_verification",
        description="Agent must acknowledge that consent has been obtained before processing PHI.",
        severity="warning",
        check_pattern=r"\bconsent\b",
    ),
]

_HEALTHCARE_TOOL_CONFIGS: list[ToolConfig] = [
    ToolConfig(
        name="phi_detector",
        description="Scans text for Protected Health Information patterns and returns redacted output.",
        required=True,
        parameters={"sensitivity": "high", "redact_mode": "replace", "log_detections": True},
    ),
    ToolConfig(
        name="audit_logger",
        description="Logs all PHI access events to the compliance audit trail.",
        required=True,
        parameters={"log_level": "INFO", "include_timestamp": True, "include_user_id": True},
    ),
    ToolConfig(
        name="medical_terminology_lookup",
        description="Retrieves standardised medical terminology and ICD code references.",
        required=False,
        parameters={"source": "icd_10", "return_codes": True},
    ),
    ToolConfig(
        name="consent_verifier",
        description="Verifies that the patient has provided valid consent for data processing.",
        required=True,
        parameters={"consent_types": ["treatment", "research", "sharing"], "strict_mode": True},
    ),
]

_HEALTHCARE_BENCHMARKS: list[EvalBenchmark] = [
    EvalBenchmark(
        name="phi_redaction_precision",
        metric="precision",
        threshold=0.99,
        description="Fraction of detected PHI instances that are genuine PHI (low false-positive rate).",
    ),
    EvalBenchmark(
        name="phi_redaction_recall",
        metric="recall",
        threshold=0.99,
        description="Fraction of actual PHI instances that are detected and redacted.",
    ),
    EvalBenchmark(
        name="disclaimer_presence_rate",
        metric="coverage",
        threshold=1.0,
        description="All responses must include the required medical-advice disclaimer.",
    ),
    EvalBenchmark(
        name="audit_log_completeness",
        metric="coverage",
        threshold=1.0,
        description="Every PHI-touching transaction must produce an audit log entry.",
    ),
    EvalBenchmark(
        name="scope_compliance_rate",
        metric="pass_rate",
        threshold=0.95,
        description="Responses must remain within the documented scope (no diagnoses, no prescribing).",
    ),
]

HEALTHCARE_HIPAA_TEMPLATE = DomainTemplate(
    metadata=_meta(
        name="healthcare_hipaa",
        domain="healthcare",
        description=(
            "HIPAA-aligned healthcare agent template for patient data handling, "
            "clinical documentation, and care coordination. Includes PHI detection "
            "rules, audit logging, consent verification, and medical terminology safety."
        ),
        frameworks=[ComplianceFramework.HIPAA, ComplianceFramework.SOC2],
        risk_level=RiskLevel.HIGH,
        tags=["healthcare", "hipaa", "phi", "clinical", "audit"],
    ),
    system_prompt=(
        "You are a HIPAA-compliant healthcare assistant. You help clinicians and "
        "patients with clinical documentation, care coordination, and general health "
        "information. You never diagnose conditions, prescribe medications, or expose "
        "Protected Health Information beyond what is necessary for the immediate task. "
        "Every response must include a disclaimer that it does not constitute medical "
        "advice. Refer users to consult a licensed clinician for any care decisions."
    ),
    tool_configs=_HEALTHCARE_TOOL_CONFIGS,
    safety_rules=_HEALTHCARE_SAFETY_RULES,
    governance_policies={
        "data_retention_days": 90,
        "require_audit_trail": True,
        "minimum_consent_level": "explicit",
        "phi_access_logging": "mandatory",
        "breach_notification_sla_hours": 72,
    },
    eval_benchmarks=_HEALTHCARE_BENCHMARKS,
    compliance_evidence={
        "HIPAA": (
            "Template enforces PHI detection and redaction, prohibits diagnostic "
            "statements, mandates audit logging of all PHI-touching interactions, "
            "and requires explicit consent verification before processing identifiable data."
        ),
        "SOC2": (
            "Audit trail tool provides immutable logs for availability and confidentiality "
            "controls. PHI detector supports the security trust service criterion."
        ),
    },
)


# ---------------------------------------------------------------------------
# Template 2 — Finance / SOX
# ---------------------------------------------------------------------------

_FINANCE_SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        rule_id="sox.no_buy_recommendation",
        description="Agent must not make specific securities buy recommendations.",
        severity="critical",
        check_pattern=r"\byou\s+should\s+(buy|purchase|acquire)\b",
    ),
    SafetyRule(
        rule_id="sox.no_guaranteed_returns",
        description="Agent must not guarantee investment returns.",
        severity="critical",
        check_pattern=r"\bguaranteed?\s+(return|profit|gain)s?\b",
    ),
    SafetyRule(
        rule_id="sox.require_investment_advice_disclaimer",
        description="Response must contain a 'not investment advice' disclaimer.",
        severity="error",
        check_pattern=r"(not\s+investment\s+advice|does\s+not\s+constitute\s+investment\s+advice)",
    ),
    SafetyRule(
        rule_id="sox.require_past_performance_disclaimer",
        description="Response must include the past-performance disclaimer.",
        severity="error",
        check_pattern=r"past\s+performance\s+(does\s+not|is\s+not)",
    ),
    SafetyRule(
        rule_id="sox.transaction_audit_pattern",
        description="All financial transaction references must include a transaction ID.",
        severity="warning",
        check_pattern=r"\btxn[-_]?id\b|\btransaction[-_]?id\b",
    ),
    SafetyRule(
        rule_id="sox.no_insider_trading_language",
        description="Agent must not produce language that could facilitate insider trading.",
        severity="critical",
        check_pattern=r"\bnon[-\s]?public\s+(material\s+)?information\b",
    ),
    SafetyRule(
        rule_id="sox.anti_fraud_pattern",
        description="Detect patterns commonly associated with financial fraud instructions.",
        severity="critical",
        check_pattern=r"\b(launder|money\s+laundering|structuring\s+transactions)\b",
    ),
    SafetyRule(
        rule_id="sox.segregation_of_duties_check",
        description="Flag operations that attempt to combine initiator and approver roles.",
        severity="warning",
        check_pattern=r"\b(self[-\s]?approve|bypass\s+approval|skip\s+review)\b",
    ),
]

_FINANCE_TOOL_CONFIGS: list[ToolConfig] = [
    ToolConfig(
        name="transaction_audit_trail",
        description="Records all financial transaction events to the immutable audit ledger.",
        required=True,
        parameters={"immutable": True, "include_hash": True, "retention_years": 7},
    ),
    ToolConfig(
        name="regulatory_reporting_validator",
        description="Validates financial outputs against regulatory reporting schemas.",
        required=True,
        parameters={"frameworks": ["SOX", "SEC"], "strict_mode": True},
    ),
    ToolConfig(
        name="fraud_signal_detector",
        description="Analyses transaction patterns for known fraud indicators.",
        required=True,
        parameters={"sensitivity": "high", "alert_on_detection": True},
    ),
    ToolConfig(
        name="financial_data_integrity_checker",
        description="Validates the mathematical integrity of financial data.",
        required=False,
        parameters={"precision": "decimal_18_6", "reconcile_on_write": True},
    ),
    ToolConfig(
        name="approval_workflow_enforcer",
        description="Enforces segregation of duties by requiring dual-approval for high-value operations.",
        required=True,
        parameters={"threshold_amount": 10000, "require_second_approver": True},
    ),
]

_FINANCE_BENCHMARKS: list[EvalBenchmark] = [
    EvalBenchmark(
        name="disclaimer_coverage_rate",
        metric="coverage",
        threshold=1.0,
        description="All financial responses must include the required investment-advice disclaimer.",
    ),
    EvalBenchmark(
        name="fraud_detection_recall",
        metric="recall",
        threshold=0.95,
        description="Fraction of simulated fraud-pattern queries correctly flagged.",
    ),
    EvalBenchmark(
        name="audit_trail_completeness",
        metric="coverage",
        threshold=1.0,
        description="Every transaction-touching interaction must produce an audit log entry.",
    ),
    EvalBenchmark(
        name="scope_compliance_rate",
        metric="pass_rate",
        threshold=0.98,
        description="Responses must not include buy/sell recommendations or guaranteed returns.",
    ),
]

FINANCE_SOX_TEMPLATE = DomainTemplate(
    metadata=_meta(
        name="finance_sox",
        domain="finance",
        description=(
            "SOX-aligned finance agent template covering transaction audit trails, "
            "financial data integrity, segregation of duties enforcement, anti-fraud "
            "detection patterns, and regulatory reporting safety."
        ),
        frameworks=[ComplianceFramework.SOX, ComplianceFramework.SOC2],
        risk_level=RiskLevel.HIGH,
        tags=["finance", "sox", "audit", "anti-fraud", "regulatory"],
    ),
    system_prompt=(
        "You are a SOX-compliant financial operations assistant. You support analysts "
        "and auditors with financial data review, regulatory reporting, and transaction "
        "analysis. You never make specific investment recommendations or guarantee returns. "
        "All responses must include a disclaimer that they do not constitute investment "
        "advice and that past performance does not guarantee future results. You escalate "
        "any indicators of fraud or policy violations immediately."
    ),
    tool_configs=_FINANCE_TOOL_CONFIGS,
    safety_rules=_FINANCE_SAFETY_RULES,
    governance_policies={
        "audit_retention_years": 7,
        "require_dual_approval_above": 10000,
        "fraud_alert_escalation": "immediate",
        "regulatory_reporting_frequency": "quarterly",
        "data_classification": "confidential",
    },
    eval_benchmarks=_FINANCE_BENCHMARKS,
    compliance_evidence={
        "SOX": (
            "Transaction audit trail provides immutable records satisfying Section 404 "
            "internal controls. Segregation of duties enforced via approval workflow. "
            "Anti-fraud patterns aligned with COSO framework requirements."
        ),
        "SOC2": (
            "Confidentiality and availability controls supported by immutable audit ledger "
            "and real-time fraud signal detection."
        ),
    },
)


# ---------------------------------------------------------------------------
# Template 3 — Customer Service
# ---------------------------------------------------------------------------

_CUSTOMER_SERVICE_SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        rule_id="cs.pii_redaction_email",
        description="Redact email addresses from logged outputs.",
        severity="error",
        check_pattern=r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
    ),
    SafetyRule(
        rule_id="cs.pii_redaction_phone",
        description="Redact phone numbers from logged outputs.",
        severity="error",
        check_pattern=r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    ),
    SafetyRule(
        rule_id="cs.escalation_trigger_urgent",
        description="Detect urgent escalation keywords and route to a human agent.",
        severity="critical",
        check_pattern=r"\b(urgent|emergency|threatening|abuse|legal\s+action|attorney)\b",
    ),
    SafetyRule(
        rule_id="cs.no_commitment_without_authorisation",
        description="Agent must not make financial commitments without explicit authorisation.",
        severity="error",
        check_pattern=r"\bwe\s+will\s+(refund|compensate|pay|reimburse)\s+\$?\d+",
    ),
    SafetyRule(
        rule_id="cs.require_ticket_reference",
        description="Responses involving account changes must reference a support ticket ID.",
        severity="warning",
        check_pattern=r"\b(ticket|case|ref|reference)[-_\s]?(number|id|#)?\s*[:#]?\s*\w+",
    ),
    SafetyRule(
        rule_id="cs.sentiment_negative_detection",
        description="Detect strong negative sentiment to trigger empathy escalation protocol.",
        severity="warning",
        check_pattern=r"\b(furious|disgusted|outraged|terrible\s+service|worst\s+company)\b",
    ),
]

_CUSTOMER_SERVICE_TOOL_CONFIGS: list[ToolConfig] = [
    ToolConfig(
        name="sentiment_analyser",
        description="Analyses customer message sentiment and returns a score from -1.0 to +1.0.",
        required=True,
        parameters={"model": "lexicon_v2", "threshold_escalate": -0.6},
    ),
    ToolConfig(
        name="pii_redactor",
        description="Detects and redacts PII before logging or storage.",
        required=True,
        parameters={"entities": ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"], "redact_char": "*"},
    ),
    ToolConfig(
        name="human_escalation_router",
        description="Routes conversations to a human agent queue when escalation criteria are met.",
        required=True,
        parameters={"queues": ["tier_1", "tier_2", "vip"], "priority_on_escalation": "high"},
    ),
    ToolConfig(
        name="crm_account_lookup",
        description="Retrieves account information from the CRM system.",
        required=False,
        parameters={"fields": ["name", "tier", "open_cases"], "read_only": True},
    ),
]

_CUSTOMER_SERVICE_BENCHMARKS: list[EvalBenchmark] = [
    EvalBenchmark(
        name="escalation_trigger_accuracy",
        metric="f1_score",
        threshold=0.90,
        description="Accuracy of identifying conversations that require human escalation.",
    ),
    EvalBenchmark(
        name="pii_redaction_recall",
        metric="recall",
        threshold=0.99,
        description="Fraction of PII instances correctly redacted before logging.",
    ),
    EvalBenchmark(
        name="first_contact_resolution_rate",
        metric="pass_rate",
        threshold=0.75,
        description="Fraction of issues resolved in a single interaction without escalation.",
    ),
    EvalBenchmark(
        name="customer_satisfaction_proxy",
        metric="sentiment_score",
        threshold=0.70,
        description="Average post-interaction sentiment score (proxy for CSAT) on 0.0–1.0 scale.",
    ),
    EvalBenchmark(
        name="response_time_sla",
        metric="pass_rate",
        threshold=0.95,
        description="Fraction of responses delivered within the configured SLA window.",
    ),
]

CUSTOMER_SERVICE_TEMPLATE = DomainTemplate(
    metadata=_meta(
        name="customer_service",
        domain="customer_service",
        description=(
            "Sentiment-aware customer service template with PII redaction, escalation "
            "triggers, response quality benchmarks, and satisfaction metrics. Suitable "
            "for general enterprise customer support workflows."
        ),
        frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOC2],
        risk_level=RiskLevel.MEDIUM,
        tags=["customer_service", "pii", "escalation", "sentiment", "gdpr"],
    ),
    system_prompt=(
        "You are a professional customer service assistant. You help customers resolve "
        "issues, answer product questions, and manage account requests. You treat every "
        "customer with empathy and respect. You never share one customer's data with "
        "another. If a customer expresses urgency, distress, or requests legal action, "
        "immediately route the conversation to a human agent. You never make financial "
        "commitments without explicit management authorisation."
    ),
    tool_configs=_CUSTOMER_SERVICE_TOOL_CONFIGS,
    safety_rules=_CUSTOMER_SERVICE_SAFETY_RULES,
    governance_policies={
        "data_retention_days": 180,
        "pii_logging_enabled": False,
        "escalation_sla_minutes": 5,
        "max_automated_refund_amount": 0,
        "gdpr_right_to_erasure_supported": True,
    },
    eval_benchmarks=_CUSTOMER_SERVICE_BENCHMARKS,
    compliance_evidence={
        "GDPR": (
            "PII redactor prevents storage of personal data in logs. Right-to-erasure "
            "workflow supported via CRM integration. Data retention policy enforces the "
            "storage-limitation principle."
        ),
        "SOC2": (
            "Confidentiality control supported by PII redaction before logging. Availability "
            "SLA benchmark enforces responsiveness commitments."
        ),
    },
)


# ---------------------------------------------------------------------------
# Template 4 — Content Moderation
# ---------------------------------------------------------------------------

_CONTENT_MODERATION_SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        rule_id="mod.toxicity_hate_speech",
        description="Detect hate speech targeting protected characteristics.",
        severity="critical",
        check_pattern=(
            r"\b(hate|kill|exterminate|genocide)\s+(all\s+)?"
            r"(jews|muslims|christians|blacks|whites|gays|trans)\b"
        ),
    ),
    SafetyRule(
        rule_id="mod.sexually_explicit_content",
        description="Detect sexually explicit language not suitable for general audiences.",
        severity="critical",
        check_pattern=r"\b(explicit\s+sexual|pornographic|nsfw\s+content)\b",
    ),
    SafetyRule(
        rule_id="mod.violence_graphic",
        description="Detect descriptions of graphic real-world violence.",
        severity="critical",
        check_pattern=r"\b(detailed\s+instructions?\s+to\s+harm|step[-\s]by[-\s]step\s+kill)\b",
    ),
    SafetyRule(
        rule_id="mod.age_appropriate_minor_context",
        description="Detect adult-audience content in contexts tagged for minors.",
        severity="error",
        check_pattern=r"\b(adult\s+content|18\+|mature\s+audiences?\s+only)\b",
    ),
    SafetyRule(
        rule_id="mod.bias_monitoring_stereotype",
        description="Detect overt demographic stereotypes in generated content.",
        severity="error",
        check_pattern=r"\b(all\s+\w+\s+are\s+(lazy|criminals|terrorists|stupid))\b",
    ),
    SafetyRule(
        rule_id="mod.require_appeal_process_notice",
        description="Moderation decisions must include notice of the appeal process.",
        severity="warning",
        check_pattern=r"\b(appeal|dispute|contest)\s+(this\s+)?(decision|removal|action)\b",
    ),
    SafetyRule(
        rule_id="mod.transparency_moderation_reason",
        description="Moderation actions must include a human-readable reason.",
        severity="error",
        check_pattern=r"\b(removed|flagged|blocked)\s+(because|due\s+to|for\s+violating)\b",
    ),
]

_CONTENT_MODERATION_TOOL_CONFIGS: list[ToolConfig] = [
    ToolConfig(
        name="toxicity_classifier",
        description="Classifies text for toxicity, hate speech, and harmful content categories.",
        required=True,
        parameters={"categories": ["toxicity", "hate_speech", "violence", "sexual"], "threshold": 0.8},
    ),
    ToolConfig(
        name="bias_monitor",
        description="Analyses content for demographic bias and stereotype patterns.",
        required=True,
        parameters={"protected_attributes": ["race", "religion", "gender", "sexuality", "age"]},
    ),
    ToolConfig(
        name="age_gate_classifier",
        description="Classifies content appropriateness by audience age tier.",
        required=True,
        parameters={"tiers": ["all_ages", "teen", "adult"], "strict_mode": True},
    ),
    ToolConfig(
        name="appeal_queue_manager",
        description="Manages the content appeal workflow, tracking open and resolved disputes.",
        required=False,
        parameters={"sla_hours": 72, "auto_escalate_after_hours": 48},
    ),
    ToolConfig(
        name="audit_decision_logger",
        description="Logs all moderation decisions with rationale for transparency reporting.",
        required=True,
        parameters={"include_classifier_score": True, "retention_days": 365},
    ),
]

_CONTENT_MODERATION_BENCHMARKS: list[EvalBenchmark] = [
    EvalBenchmark(
        name="toxicity_detection_precision",
        metric="precision",
        threshold=0.92,
        description="Fraction of content flagged as toxic that is genuinely policy-violating.",
    ),
    EvalBenchmark(
        name="toxicity_detection_recall",
        metric="recall",
        threshold=0.95,
        description="Fraction of policy-violating content that is correctly detected.",
    ),
    EvalBenchmark(
        name="false_positive_rate",
        metric="false_positive_rate",
        threshold=0.05,
        description="Maximum acceptable rate of benign content incorrectly flagged.",
    ),
    EvalBenchmark(
        name="appeal_resolution_rate",
        metric="pass_rate",
        threshold=0.90,
        description="Fraction of content appeals resolved within the configured SLA.",
    ),
]

CONTENT_MODERATION_TEMPLATE = DomainTemplate(
    metadata=_meta(
        name="content_moderation",
        domain="content_moderation",
        description=(
            "Content moderation template with toxicity detection, demographic bias "
            "monitoring, age-appropriate content classification, appeal process safety, "
            "and transparency requirements for moderation decisions."
        ),
        frameworks=[ComplianceFramework.GDPR, ComplianceFramework.NONE],
        risk_level=RiskLevel.MEDIUM,
        tags=["content_moderation", "toxicity", "bias", "transparency", "appeals"],
    ),
    system_prompt=(
        "You are a content moderation assistant. You review user-generated content "
        "against platform policies and classify it for action. For every moderation "
        "decision you provide a clear, human-readable reason referencing the specific "
        "policy violated. You include notice of the content appeal process in all "
        "removal decisions. You do not apply moderation based on political viewpoints "
        "or personal opinions — only on documented policy violations."
    ),
    tool_configs=_CONTENT_MODERATION_TOOL_CONFIGS,
    safety_rules=_CONTENT_MODERATION_SAFETY_RULES,
    governance_policies={
        "appeal_sla_hours": 72,
        "auto_remove_above_confidence": 0.95,
        "human_review_required_above_confidence": 0.80,
        "transparency_report_frequency": "quarterly",
        "bias_audit_frequency": "monthly",
    },
    eval_benchmarks=_CONTENT_MODERATION_BENCHMARKS,
    compliance_evidence={
        "GDPR": (
            "All moderation decisions are logged with rationale. Users are informed of "
            "their right to appeal, satisfying transparency obligations. PII in flagged "
            "content is handled in line with data-minimisation principles."
        ),
    },
)


# ---------------------------------------------------------------------------
# Template 5 — Research Assistant
# ---------------------------------------------------------------------------

_RESEARCH_ASSISTANT_SAFETY_RULES: list[SafetyRule] = [
    SafetyRule(
        rule_id="research.require_citation",
        description="All factual claims must be accompanied by a citation.",
        severity="error",
        check_pattern=r"\[(\d+|[A-Z][a-z]+\s+et\s+al\.?,?\s+\d{4}|[A-Z][a-z]+,?\s+\d{4})\]",
    ),
    SafetyRule(
        rule_id="research.source_attribution_doi",
        description="Citations must include a DOI or equivalent stable identifier where available.",
        severity="warning",
        check_pattern=r"\b(doi\.org|arxiv\.org|pubmed\.ncbi\.nlm\.nih\.gov)\b",
    ),
    SafetyRule(
        rule_id="research.confidence_qualifier",
        description="Uncertain claims must be qualified with appropriate epistemic hedges.",
        severity="error",
        check_pattern=(
            r"\b(may|might|could|appears\s+to|suggests?|according\s+to|evidence\s+indicates?)\b"
        ),
    ),
    SafetyRule(
        rule_id="research.no_fabricated_citation",
        description="Agent must not fabricate author names, journal names, or DOIs.",
        severity="critical",
        check_pattern=r"\b(smith\s+et\s+al\.,?\s+2024|journal\s+of\s+ai\s+research)\b",
    ),
    SafetyRule(
        rule_id="research.academic_integrity_notice",
        description="Outputs intended for academic submission must include an academic-integrity notice.",
        severity="warning",
        check_pattern=r"\b(academic\s+integrity|original\s+work|ai[-\s]?generated\s+disclosure)\b",
    ),
    SafetyRule(
        rule_id="research.methodology_disclosure",
        description="Research summaries must disclose the methodology used for source selection.",
        severity="warning",
        check_pattern=r"\b(methodology|search\s+strategy|inclusion\s+criteria|prisma)\b",
    ),
]

_RESEARCH_ASSISTANT_TOOL_CONFIGS: list[ToolConfig] = [
    ToolConfig(
        name="citation_verifier",
        description="Verifies that cited DOIs resolve to real publications and checks metadata accuracy.",
        required=True,
        parameters={"verify_doi": True, "check_metadata": True, "flag_retracted": True},
    ),
    ToolConfig(
        name="source_attribution_tracker",
        description="Tracks all knowledge sources used in a response for reproducibility.",
        required=True,
        parameters={"output_format": "apa_7", "include_access_date": True},
    ),
    ToolConfig(
        name="confidence_calibrator",
        description="Assigns confidence scores to factual claims based on source quality and consensus.",
        required=True,
        parameters={"scale": "0_to_1", "low_confidence_threshold": 0.6},
    ),
    ToolConfig(
        name="academic_database_search",
        description="Searches PubMed, arXiv, and Semantic Scholar for peer-reviewed sources.",
        required=False,
        parameters={"databases": ["pubmed", "arxiv", "semantic_scholar"], "max_results": 20},
    ),
    ToolConfig(
        name="plagiarism_detector",
        description="Checks generated text for excessive similarity to source material.",
        required=False,
        parameters={"similarity_threshold": 0.30, "exclude_citations": True},
    ),
]

_RESEARCH_ASSISTANT_BENCHMARKS: list[EvalBenchmark] = [
    EvalBenchmark(
        name="citation_accuracy_rate",
        metric="precision",
        threshold=0.95,
        description="Fraction of citations that resolve to real, correctly attributed publications.",
    ),
    EvalBenchmark(
        name="confidence_calibration_error",
        metric="calibration_error",
        threshold=0.10,
        description="Maximum expected calibration error between stated and empirical confidence.",
    ),
    EvalBenchmark(
        name="source_coverage_recall",
        metric="recall",
        threshold=0.85,
        description="Fraction of relevant sources retrieved relative to a gold-standard reference set.",
    ),
    EvalBenchmark(
        name="factual_accuracy_rate",
        metric="pass_rate",
        threshold=0.90,
        description="Fraction of factual claims verified against the cited source material.",
    ),
    EvalBenchmark(
        name="academic_integrity_compliance",
        metric="coverage",
        threshold=1.0,
        description="All academically-destined outputs include the required integrity disclosure.",
    ),
]

RESEARCH_ASSISTANT_TEMPLATE = DomainTemplate(
    metadata=_meta(
        name="research_assistant",
        domain="research",
        description=(
            "Academic research assistant template with citation verification, source "
            "attribution tracking, confidence calibration, academic integrity checks, "
            "and methodology validation for peer-review-quality outputs."
        ),
        frameworks=[ComplianceFramework.NONE],
        risk_level=RiskLevel.LOW,
        tags=["research", "citation", "academic", "source_attribution", "confidence"],
    ),
    system_prompt=(
        "You are an academic research assistant. You help researchers find, synthesise, "
        "and cite peer-reviewed literature. Every factual claim you make must be supported "
        "by a cited source. You qualify uncertain claims with appropriate hedging language. "
        "You never fabricate citations, DOIs, or author names. For outputs intended for "
        "academic submission, include a disclosure that AI assistance was used and that "
        "the human author is responsible for verifying all content."
    ),
    tool_configs=_RESEARCH_ASSISTANT_TOOL_CONFIGS,
    safety_rules=_RESEARCH_ASSISTANT_SAFETY_RULES,
    governance_policies={
        "citation_style": "apa_7",
        "require_doi_when_available": True,
        "flag_retracted_papers": True,
        "confidence_disclosure_threshold": 0.6,
        "plagiarism_similarity_threshold": 0.30,
    },
    eval_benchmarks=_RESEARCH_ASSISTANT_BENCHMARKS,
    compliance_evidence={
        "NONE": (
            "Template is designed for general academic use. Citation verification and "
            "confidence calibration support factual accuracy. Academic-integrity disclosure "
            "supports ethical AI use policies."
        ),
    },
)


# ---------------------------------------------------------------------------
# TemplateLibrary
# ---------------------------------------------------------------------------

_BUILTIN_TEMPLATES: dict[str, DomainTemplate] = {
    HEALTHCARE_HIPAA_TEMPLATE.metadata.name: HEALTHCARE_HIPAA_TEMPLATE,
    FINANCE_SOX_TEMPLATE.metadata.name: FINANCE_SOX_TEMPLATE,
    CUSTOMER_SERVICE_TEMPLATE.metadata.name: CUSTOMER_SERVICE_TEMPLATE,
    CONTENT_MODERATION_TEMPLATE.metadata.name: CONTENT_MODERATION_TEMPLATE,
    RESEARCH_ASSISTANT_TEMPLATE.metadata.name: RESEARCH_ASSISTANT_TEMPLATE,
}


class TemplateNotFoundError(KeyError):
    """Raised when a requested certified template is not found in the library."""

    def __init__(self, name: str) -> None:
        self.template_name = name
        super().__init__(
            f"Certified template {name!r} is not registered. "
            "Use TemplateLibrary.list_templates() to see available templates."
        )


class TemplateLibrary:
    """Registry of :class:`~agent_vertical.certified.schema.DomainTemplate` instances.

    Initialised with the five built-in templates; supports registration of
    custom templates and import/export via YAML files.

    Example
    -------
    ::

        library = TemplateLibrary()
        names = library.list_templates()
        template = library.get_template("healthcare_hipaa")

        library.export_template("finance_sox", "/tmp/finance_sox.yaml")
        imported = library.import_template("/tmp/finance_sox.yaml")
    """

    def __init__(self) -> None:
        self._registry: dict[str, DomainTemplate] = dict(_BUILTIN_TEMPLATES)

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def get_template(self, name: str) -> DomainTemplate:
        """Return the template registered under ``name``.

        Parameters
        ----------
        name:
            Machine-readable template name.

        Returns
        -------
        DomainTemplate

        Raises
        ------
        TemplateNotFoundError
            If no template is registered under ``name``.
        """
        try:
            return self._registry[name]
        except KeyError:
            raise TemplateNotFoundError(name) from None

    def list_templates(self) -> list[str]:
        """Return a sorted list of all registered template names.

        Returns
        -------
        list[str]
        """
        return sorted(self._registry.keys())

    def register_custom(self, template: DomainTemplate) -> None:
        """Register a custom template, overwriting any existing template with the same name.

        Parameters
        ----------
        template:
            The :class:`DomainTemplate` to register.
        """
        self._registry[template.metadata.name] = template

    def unregister(self, name: str) -> None:
        """Remove a template from the registry.

        Parameters
        ----------
        name:
            Machine-readable template name.

        Raises
        ------
        TemplateNotFoundError
            If no template is registered under ``name``.
        """
        if name not in self._registry:
            raise TemplateNotFoundError(name)
        del self._registry[name]

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_by_compliance(
        self, framework: ComplianceFramework
    ) -> list[DomainTemplate]:
        """Return all templates that include ``framework`` in their compliance list.

        Parameters
        ----------
        framework:
            The :class:`~agent_vertical.certified.schema.ComplianceFramework` to filter by.

        Returns
        -------
        list[DomainTemplate]
            Templates sorted by name.
        """
        return sorted(
            [
                t
                for t in self._registry.values()
                if framework in t.metadata.compliance_frameworks
            ],
            key=lambda t: t.metadata.name,
        )

    def search_by_domain(self, domain: str) -> list[DomainTemplate]:
        """Return all templates whose metadata domain matches ``domain``.

        Parameters
        ----------
        domain:
            Domain string to match (case-insensitive prefix/exact match).

        Returns
        -------
        list[DomainTemplate]
            Templates sorted by name.
        """
        domain_lower = domain.lower()
        return sorted(
            [
                t
                for t in self._registry.values()
                if t.metadata.domain.lower() == domain_lower
            ],
            key=lambda t: t.metadata.name,
        )

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_template(self, name: str, path: str | os.PathLike[str]) -> None:
        """Serialise a template to a YAML file.

        Parameters
        ----------
        name:
            Machine-readable template name.
        path:
            Filesystem path for the output YAML file.

        Raises
        ------
        TemplateNotFoundError
            If no template is registered under ``name``.
        """
        template = self.get_template(name)
        output_path = Path(path)
        output_path.write_text(template.to_yaml(), encoding="utf-8")

    def import_template(
        self, path: str | os.PathLike[str]
    ) -> DomainTemplate:
        """Deserialise a template from a YAML file and register it.

        Parameters
        ----------
        path:
            Filesystem path of the YAML file to import.

        Returns
        -------
        DomainTemplate
            The imported template (also registered in this library).
        """
        yaml_text = Path(path).read_text(encoding="utf-8")
        template = DomainTemplate.from_yaml(yaml_text)
        self.register_custom(template)
        return template

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: object) -> bool:
        return name in self._registry

    def __repr__(self) -> str:
        names = sorted(self._registry.keys())
        return f"TemplateLibrary(templates={names})"
