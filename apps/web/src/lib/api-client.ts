/**
 * Typed fetch wrapper for the EPSCAxplor API.
 *
 * - Base URL comes from NEXT_PUBLIC_API_URL (baked at build time).
 * - Every request sends credentials so the httpOnly refresh cookie
 *   (path /auth) round-trips; JS never reads the cookie itself.
 * - The access JWT is held in memory only. On a 401 from an
 *   authenticated endpoint the client silently refreshes and retries
 *   the original request exactly once.
 */
import type {
  DocumentFilters,
  DocumentListResponse,
  QueryHistoryParams,
  QueryHistoryResponse,
  QueryResponse,
  TokenResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`API request failed (${status}): ${detail}`);
    this.name = "ApiError";
  }
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // non-JSON error body — fall through to the generic detail
  }
  return response.statusText || `request failed with status ${response.status}`;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** When true (default), attach the bearer token and refresh-retry on 401. */
  authenticated?: boolean;
}

export class ApiClient {
  private accessToken: string | null = null;
  private refreshPromise: Promise<TokenResponse> | null = null;

  constructor(private readonly baseUrl: string) {}

  getAccessToken(): string | null {
    return this.accessToken;
  }

  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const tokens = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      authenticated: false,
    });
    this.accessToken = tokens.access_token;
    return tokens;
  }

  /**
   * Exchange the httpOnly refresh cookie for a new access token.
   * Concurrent callers share a single in-flight request.
   */
  refresh(): Promise<TokenResponse> {
    this.refreshPromise ??= this.doRefresh().finally(() => {
      this.refreshPromise = null;
    });
    return this.refreshPromise;
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>("/auth/logout", {
        method: "POST",
        authenticated: false,
      });
    } finally {
      this.accessToken = null;
    }
  }

  async query(query: string): Promise<QueryResponse> {
    return this.request<QueryResponse>("/query", {
      method: "POST",
      body: { query },
    });
  }

  async listDocuments(filters: DocumentFilters = {}): Promise<DocumentListResponse> {
    const params = new URLSearchParams();
    if (filters.union_name !== undefined) params.set("union_name", filters.union_name);
    if (filters.document_type !== undefined) params.set("document_type", filters.document_type);
    if (filters.is_expired !== undefined) params.set("is_expired", String(filters.is_expired));
    return this.request<DocumentListResponse>(withQueryString("/documents", params));
  }

  async getQueryHistory(params: QueryHistoryParams = {}): Promise<QueryHistoryResponse> {
    const search = new URLSearchParams();
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    return this.request<QueryHistoryResponse>(withQueryString("/query-history", search));
  }

  private async doRefresh(): Promise<TokenResponse> {
    const response = await this.send("/auth/refresh", { method: "POST" }, false);
    if (!response.ok) {
      this.accessToken = null;
      throw new ApiError(response.status, await errorDetail(response));
    }
    const tokens = (await response.json()) as TokenResponse;
    this.accessToken = tokens.access_token;
    return tokens;
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, authenticated = true } = options;

    let response = await this.send(path, { method, body }, authenticated);
    if (response.status === 401 && authenticated) {
      // Silent refresh, then retry the original request exactly once.
      // A failed refresh throws its own 401 ApiError with the token cleared.
      await this.refresh();
      response = await this.send(path, { method, body }, authenticated);
    }

    if (!response.ok) {
      throw new ApiError(response.status, await errorDetail(response));
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  private send(
    path: string,
    { method = "GET", body }: RequestOptions,
    authenticated: boolean,
  ): Promise<Response> {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (authenticated && this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }
    return fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
    });
  }
}

function withQueryString(path: string, params: URLSearchParams): string {
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

export const apiClient = new ApiClient(process.env.NEXT_PUBLIC_API_URL ?? "");
