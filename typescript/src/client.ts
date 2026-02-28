/**
 * HTTP client for the agent-vertical domain template API.
 *
 * Uses the Fetch API (available natively in Node 18+, browsers, and Deno).
 * No external dependencies required.
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

import type {
  ApiError,
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
// Internal helpers
// ---------------------------------------------------------------------------

async function fetchJson<T>(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    clearTimeout(timeoutId);

    const body = await response.json() as unknown;

    if (!response.ok) {
      const errorBody = body as Partial<ApiError>;
      return {
        ok: false,
        error: {
          error: errorBody.error ?? "Unknown error",
          detail: errorBody.detail ?? "",
        },
        status: response.status,
      };
    }

    return { ok: true, data: body as T };
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: { error: "Network error", detail: message },
      status: 0,
    };
  }
}

function buildHeaders(
  extraHeaders: Readonly<Record<string, string>> | undefined,
): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...extraHeaders,
  };
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
  const { baseUrl, timeoutMs = 30_000, headers: extraHeaders } = config;
  const baseHeaders = buildHeaders(extraHeaders);

  return {
    async getTemplates(options?: {
      domain?: string;
      limit?: number;
    }): Promise<ApiResult<readonly DomainTemplate[]>> {
      const params = new URLSearchParams();
      if (options?.domain !== undefined) {
        params.set("domain", options.domain);
      }
      if (options?.limit !== undefined) {
        params.set("limit", String(options.limit));
      }
      const query = params.toString();
      return fetchJson<readonly DomainTemplate[]>(
        `${baseUrl}/vertical/templates${query ? `?${query}` : ""}`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async applyTemplate(
      templateConfig: TemplateConfig,
    ): Promise<ApiResult<DomainTemplate>> {
      return fetchJson<DomainTemplate>(
        `${baseUrl}/vertical/templates/apply`,
        {
          method: "POST",
          headers: baseHeaders,
          body: JSON.stringify(templateConfig),
        },
        timeoutMs,
      );
    },

    async validateTemplate(
      templateName: string,
    ): Promise<ApiResult<TemplateValidationResult>> {
      return fetchJson<TemplateValidationResult>(
        `${baseUrl}/vertical/templates/${encodeURIComponent(templateName)}/validate`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async getToolCollection(options: {
      domain?: string;
      template_name?: string;
    }): Promise<ApiResult<ToolCollection>> {
      const params = new URLSearchParams();
      if (options.domain !== undefined) {
        params.set("domain", options.domain);
      }
      if (options.template_name !== undefined) {
        params.set("template_name", options.template_name);
      }
      return fetchJson<ToolCollection>(
        `${baseUrl}/vertical/tools?${params.toString()}`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async getDomainConfig(domain: string): Promise<ApiResult<DomainConfig>> {
      return fetchJson<DomainConfig>(
        `${baseUrl}/vertical/domains/${encodeURIComponent(domain)}/config`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async getPromptPattern(domain: string): Promise<ApiResult<PromptPattern>> {
      return fetchJson<PromptPattern>(
        `${baseUrl}/vertical/domains/${encodeURIComponent(domain)}/rules`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async listDomains(): Promise<ApiResult<readonly string[]>> {
      return fetchJson<readonly string[]>(
        `${baseUrl}/vertical/domains`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },

    async getTemplate(templateName: string): Promise<ApiResult<DomainTemplate>> {
      return fetchJson<DomainTemplate>(
        `${baseUrl}/vertical/templates/${encodeURIComponent(templateName)}`,
        { method: "GET", headers: baseHeaders },
        timeoutMs,
      );
    },
  };
}

/** Re-export types for convenience. */
export type {
  DomainConfig,
  DomainTemplate,
  PromptPattern,
  TemplateConfig,
  TemplateValidationResult,
  ToolCollection,
};
