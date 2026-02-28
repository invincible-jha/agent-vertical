/**
 * TypeScript interfaces for the agent-vertical domain template system.
 *
 * Mirrors the Python dataclasses and Pydantic models defined in:
 *   agent_vertical.templates.base          (DomainTemplate, TemplateRegistry)
 *   agent_vertical.certified.schema        (SafetyRule, ToolConfig, EvalBenchmark, TemplateMetadata, DomainTemplate)
 *   agent_vertical.compliance.domain_rules (RuleType, ComplianceRule, DomainComplianceRules)
 *   agent_vertical.certification.risk_tier (RiskTier)
 *
 * All interfaces use readonly fields to match Python frozen dataclasses.
 */

// ---------------------------------------------------------------------------
// Risk and compliance enums
// ---------------------------------------------------------------------------

/**
 * Risk classification tiers for domain templates.
 * Maps to RiskTier / RiskLevel enums in Python.
 */
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/**
 * Recognised compliance and regulatory frameworks.
 * Maps to ComplianceFramework enum in Python.
 */
export type ComplianceFramework =
  | "HIPAA"
  | "SOX"
  | "GDPR"
  | "SOC2"
  | "PCI_DSS"
  | "NONE";

/**
 * The type of compliance rule.
 * Maps to RuleType enum in Python.
 */
export type RuleType =
  | "PROHIBITED_PHRASE"
  | "REQUIRED_DISCLAIMER"
  | "PROHIBITED_PATTERN"
  | "REQUIRED_PATTERN";

// ---------------------------------------------------------------------------
// Safety rule
// ---------------------------------------------------------------------------

/**
 * A single safety constraint applied to agent output at runtime.
 * Maps to SafetyRule frozen dataclass in Python.
 */
export interface SafetyRule {
  /** Unique dot-notation identifier (e.g. "hipaa.no_phi_exposure"). */
  readonly rule_id: string;
  /** Human-readable description of the constraint. */
  readonly description: string;
  /** Impact level: "warning", "error", or "critical". */
  readonly severity: string;
  /** Python regex pattern used to test agent output. */
  readonly check_pattern: string;
}

// ---------------------------------------------------------------------------
// Tool collection / config
// ---------------------------------------------------------------------------

/**
 * Configuration for a single tool available to the agent.
 * Maps to ToolConfig frozen dataclass in Python.
 */
export interface ToolConfig {
  /** Machine-readable tool name (e.g. "audit_logger"). */
  readonly name: string;
  /** Human-readable description of what the tool does. */
  readonly description: string;
  /** When true, the tool must be wired up before the template is deployable. */
  readonly required: boolean;
  /** Parameter schema for the tool. */
  readonly parameters: Readonly<Record<string, unknown>>;
}

/**
 * A named collection of tool configurations for a domain.
 * Corresponds to the tools tuple on DomainTemplate in Python.
 */
export interface ToolCollection {
  /** Name of this tool collection (typically matching the template domain). */
  readonly collection_name: string;
  /** The tool configurations in this collection. */
  readonly tools: readonly ToolConfig[];
}

// ---------------------------------------------------------------------------
// Evaluation metric
// ---------------------------------------------------------------------------

/**
 * A single evaluation benchmark specification.
 * Maps to EvalBenchmark frozen dataclass in Python.
 */
export interface EvaluationMetric {
  /** Short identifier for the benchmark (e.g. "phi_redaction_rate"). */
  readonly name: string;
  /** The measurement being tracked (e.g. "precision", "recall"). */
  readonly metric: string;
  /** Minimum acceptable value on a 0.0–1.0 scale. */
  readonly threshold: number;
  /** Human-readable description of what this benchmark verifies. */
  readonly description: string;
}

// ---------------------------------------------------------------------------
// Template metadata
// ---------------------------------------------------------------------------

/** Provenance and classification metadata for a DomainTemplate. */
export interface TemplateMetadata {
  /** Unique machine-readable template name. */
  readonly name: string;
  /** Semantic version string (e.g. "1.0.0"). */
  readonly version: string;
  /** Domain this template belongs to (e.g. "healthcare"). */
  readonly domain: string;
  /** Compliance frameworks the template is designed to satisfy. */
  readonly compliance_frameworks: readonly ComplianceFramework[];
  /** Risk classification for this template. */
  readonly risk_level: RiskLevel;
  /** Human-readable description of the template's purpose. */
  readonly description: string;
  /** Author or team identifier. */
  readonly author: string;
  /** ISO-8601 UTC datetime of initial template creation. */
  readonly created_at: string;
  /** Free-form tags for search and filtering. */
  readonly tags: readonly string[];
}

// ---------------------------------------------------------------------------
// Domain template (the central entity)
// ---------------------------------------------------------------------------

/**
 * A compliance-certified, self-describing agent template.
 * Maps to DomainTemplate Pydantic model in Python (certified.schema).
 */
export interface DomainTemplate {
  /** Provenance and classification metadata. */
  readonly metadata: TemplateMetadata;
  /** Full system prompt for the LLM context. */
  readonly system_prompt: string;
  /** Tool declarations with required/optional flags. */
  readonly tool_configs: readonly ToolConfig[];
  /** Runtime safety constraints with regex patterns. */
  readonly safety_rules: readonly SafetyRule[];
  /** Free-form governance policies (key/value). */
  readonly governance_policies: Readonly<Record<string, unknown>>;
  /** Evaluation benchmarks with numeric thresholds. */
  readonly eval_benchmarks: readonly EvaluationMetric[];
  /** Mapping of framework name to compliance evidence description. */
  readonly compliance_evidence: Readonly<Record<string, string>>;
}

/** Configuration options for applying a template to an agent. */
export interface TemplateConfig {
  /** The template name to apply. */
  readonly template_name: string;
  /** Optional parameter overrides for this deployment. */
  readonly parameter_overrides?: Readonly<Record<string, unknown>>;
  /** Whether to perform pre-apply validation. */
  readonly validate_before_apply?: boolean;
}

// ---------------------------------------------------------------------------
// Compliance rule
// ---------------------------------------------------------------------------

/**
 * A single domain compliance rule.
 * Maps to ComplianceRule frozen dataclass in Python.
 */
export interface ComplianceRule {
  /** Unique identifier in dot notation (e.g. "hipaa.no_diagnosis"). */
  readonly rule_id: string;
  /** Whether this rule prohibits or requires content. */
  readonly rule_type: RuleType;
  /** The phrase or regex pattern to test against agent responses. */
  readonly pattern: string;
  /** Human-readable description of what this rule enforces. */
  readonly description: string;
  /** Impact level: "critical", "high", "medium", or "low". */
  readonly severity: string;
  /** Suggested fix when this rule is violated. */
  readonly remediation: string;
  /** When true, pattern is treated as a regular expression. */
  readonly is_regex: boolean;
}

/** A collection of compliance rules for a specific domain. */
export interface PromptPattern {
  /** Domain identifier (e.g. "healthcare"). */
  readonly domain: string;
  /** Ordered list of rules to enforce. */
  readonly rules: readonly ComplianceRule[];
}

// ---------------------------------------------------------------------------
// Template validation result
// ---------------------------------------------------------------------------

/** Result of validating a domain template. */
export interface TemplateValidationResult {
  /** Whether the template passed all validation checks. */
  readonly valid: boolean;
  /** Human-readable warning messages (non-empty means issues found). */
  readonly warnings: readonly string[];
  /** The template name that was validated. */
  readonly template_name: string;
}

// ---------------------------------------------------------------------------
// Domain config summary
// ---------------------------------------------------------------------------

/** Summary configuration for a specific domain. */
export interface DomainConfig {
  /** Domain identifier. */
  readonly domain: string;
  /** Available templates in this domain. */
  readonly templates: readonly string[];
  /** Compliance rules applicable to this domain. */
  readonly compliance_rules: readonly ComplianceRule[];
  /** Supported compliance frameworks for this domain. */
  readonly supported_frameworks: readonly ComplianceFramework[];
}

// ---------------------------------------------------------------------------
// API result wrapper (shared pattern)
// ---------------------------------------------------------------------------

/** Standard error payload returned by the agent-vertical API. */
export interface ApiError {
  readonly error: string;
  readonly detail: string;
}

/** Result type for all client operations. */
export type ApiResult<T> =
  | { readonly ok: true; readonly data: T }
  | { readonly ok: false; readonly error: ApiError; readonly status: number };
