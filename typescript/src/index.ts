/**
 * @aumos/agent-vertical
 *
 * TypeScript client for the AumOS agent-vertical domain template system.
 * Provides HTTP client, certified domain templates, safety rules, tool collections,
 * compliance rules, and evaluation metric type definitions.
 */

// Client and configuration
export type { AgentVerticalClient, AgentVerticalClientConfig } from "./client.js";
export { createAgentVerticalClient } from "./client.js";

// Core types
export type {
  ApiError,
  ApiResult,
  ComplianceFramework,
  ComplianceRule,
  DomainConfig,
  DomainTemplate,
  EvaluationMetric,
  PromptPattern,
  RiskLevel,
  RuleType,
  SafetyRule,
  TemplateConfig,
  TemplateMetadata,
  TemplateValidationResult,
  ToolCollection,
  ToolConfig,
} from "./types.js";
