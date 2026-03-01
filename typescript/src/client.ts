/**
 * HTTP client for the agent-vertical domain template API.
 *
 * Delegates all HTTP transport to `@aumos/sdk-core` which provides
 * automatic retry with exponential back-off, timeout management via
 * `AbortSignal.timeout`, interceptor support, and a typed error hierarchy.
 *
 * The public-facing `ApiResult<T>` envelope is preserved for full
 * backward compatibility with existing callers.
 *
 * @example
 * ```ts
 * import { createAgentVerticalClient } from "@aumos/agent-vertical";
 *
 * const client = createAgentVerticalClient({ baseUrl: "http://localhost:8093" });
 *
 * const templates = await client.getTemplates({ domain: "healthcare" });
 *
 * if (templates.ok) {
 *   console.log("Available templates:", templates.data.map(t => t.metadata.name));
 * }
 * ```
 */

import {
  createHttpClient,
  HttpError,
  NetworkError,
  TimeoutError,
  AumosError,
  type HttpClient,
} from "@aumos/sdk-core";

import type {
  ApiResult,
  DomainConfig,
  DomainTemplate,
  PromptPattern,
  TemplateConfig,
  TemplateValidationResult,
  ToolCollection,
} from "./types.js";

// ---------------------------------------------------------------------------
// Client configuration
// ---------------------------------------------------------------------------

/** Configuration options for the AgentVerticalClient. */
export interface AgentVerticalClientConfig {
  /** Base URL of the agent-vertical server (e.g. "http://localhost:8093"). */
  readonly baseUrl: string;
  /** Optional request timeout in milliseconds (default: 30000). */
  readonly timeoutMs?: number;
  /** Optional extra HTTP headers sent with every request. */
  readonly headers?: Readonly<Record<string, string>>;
}

// ---------------------------------------------------------------------------
// Internal adapter
// ---------------------------------------------------------------------------

async function callApi<T>(
  operation: () => Promise<{ readonly data: T; readonly status: number }>,
): Promise<ApiResult<T>> {
  try {
    const response = await operation();
    return { ok: true, data: response.data };
  } catch (error: unknown) {
    if (error instanceof HttpError) {
      return {
        ok: false,
        error: { error: error.message, detail: String(error.body ?? "") },
        status: error.statusCode,
      };
    }
    if (error instanceof TimeoutError) {
      return {
        ok: false,
        error: { error: "Request timed out", detail: error.message },
        status: 0,
      };
    }
    if (error instanceof NetworkError) {
      return {
        ok: false,
        error: { error: "Network error", detail: error.message },
        status: 0,
      };
    }
    if (error instanceof AumosError) {
      return {
        ok: false,
        error: { error: error.code, detail: error.message },
        status: error.statusCode ?? 0,
      };
    }
    const message = error instanceof Error ? error.message : String(error);
    return {
      ok: false,
      error: { error: "Unexpected error", detail: message },
      status: 0,
    };
  }
}

// ---------------------------------------------------------------------------
// Client interface
// ---------------------------------------------------------------------------

/** Typed HTTP client for the agent-vertical server. */
export interface AgentVerticalClient {
  /**
   * List all registered domain templates, optionally filtered by domain.
   *
   * @param options - Optional domain filter.
   * @returns Array of DomainTemplate records sorted by full name.
   */
  getTemplates(options?: {
    domain?: string;
    limit?: number;
  }): Promise<ApiResult<readonly DomainTemplate[]>>;

  /**
   * Apply a named template to an agent deployment configuration.
   *
   * @param config - Template name and optional parameter overrides.
   * @returns The resolved DomainTemplate with applied configuration.
   */
  applyTemplate(config: TemplateConfig): Promise<ApiResult<DomainTemplate>>;

  /**
   * Validate a domain template for compliance and structural correctness.
   *
   * @param templateName - The machine-readable template name to validate.
   * @returns A TemplateValidationResult with any warnings found.
   */
  validateTemplate(
    templateName: string,
  ): Promise<ApiResult<TemplateValidationResult>>;

  /**
   * Get the tool collection for a specific domain or template.
   *
   * @param options - Domain or template name to retrieve tools for.
   * @returns A ToolCollection with all available tool configs.
   */
  getToolCollection(options: {
    domain?: string;
    template_name?: string;
  }): Promise<ApiResult<ToolCollection>>;

  /**
   * Get the domain configuration including templates and compliance rules.
   *
   * @param domain - The domain identifier (e.g. "healthcare", "finance").
   * @returns A DomainConfig with templates and compliance rules.
   */
  getDomainConfig(domain: string): Promise<ApiResult<DomainConfig>>;

  /**
   * Get the compliance prompt patterns (rules) for a domain.
   *
   * @param domain - The domain identifier.
   * @returns A PromptPattern with all ComplianceRule records for that domain.
   */
  getPromptPattern(domain: string): Promise<ApiResult<PromptPattern>>;

  /**
   * List all registered domains.
   *
   * @returns Array of domain identifier strings.
   */
  listDomains(): Promise<ApiResult<readonly string[]>>;

  /**
   * Retrieve a single template by name.
   *
   * @param templateName - The machine-readable template name.
   * @returns The DomainTemplate record.
   */
  getTemplate(templateName: string): Promise<ApiResult<DomainTemplate>>;
}

// ---------------------------------------------------------------------------
// Client factory
// ---------------------------------------------------------------------------

/**
 * Create a typed HTTP client for the agent-vertical server.
 *
 * @param config - Client configuration including base URL.
 * @returns An AgentVerticalClient instance.
 */
export function createAgentVerticalClient(
  config: AgentVerticalClientConfig,
): AgentVerticalClient {
  const http: HttpClient = createHttpClient({
    baseUrl: config.baseUrl,
    timeout: config.timeoutMs ?? 30_000,
    defaultHeaders: config.headers,
  });

  return {
    getTemplates(options?: {
      domain?: string;
      limit?: number;
    }): Promise<ApiResult<readonly DomainTemplate[]>> {
      const queryParams: Record<string, string> = {};
      if (options?.domain !== undefined) queryParams["domain"] = options.domain;
      if (options?.limit !== undefined) queryParams["limit"] = String(options.limit);
      return callApi(() =>
        http.get<readonly DomainTemplate[]>("/vertical/templates", { queryParams }),
      );
    },

    applyTemplate(templateConfig: TemplateConfig): Promise<ApiResult<DomainTemplate>> {
      return callApi(() =>
        http.post<DomainTemplate>("/vertical/templates/apply", templateConfig),
      );
    },

    validateTemplate(
      templateName: string,
    ): Promise<ApiResult<TemplateValidationResult>> {
      return callApi(() =>
        http.get<TemplateValidationResult>(
          `/vertical/templates/${encodeURIComponent(templateName)}/validate`,
        ),
      );
    },

    getToolCollection(options: {
      domain?: string;
      template_name?: string;
    }): Promise<ApiResult<ToolCollection>> {
      const queryParams: Record<string, string> = {};
      if (options.domain !== undefined) queryParams["domain"] = options.domain;
      if (options.template_name !== undefined) {
        queryParams["template_name"] = options.template_name;
      }
      return callApi(() =>
        http.get<ToolCollection>("/vertical/tools", { queryParams }),
      );
    },

    getDomainConfig(domain: string): Promise<ApiResult<DomainConfig>> {
      return callApi(() =>
        http.get<DomainConfig>(
          `/vertical/domains/${encodeURIComponent(domain)}/config`,
        ),
      );
    },

    getPromptPattern(domain: string): Promise<ApiResult<PromptPattern>> {
      return callApi(() =>
        http.get<PromptPattern>(
          `/vertical/domains/${encodeURIComponent(domain)}/rules`,
        ),
      );
    },

    listDomains(): Promise<ApiResult<readonly string[]>> {
      return callApi(() => http.get<readonly string[]>("/vertical/domains"));
    },

    getTemplate(templateName: string): Promise<ApiResult<DomainTemplate>> {
      return callApi(() =>
        http.get<DomainTemplate>(
          `/vertical/templates/${encodeURIComponent(templateName)}`,
        ),
      );
    },
  };
}
