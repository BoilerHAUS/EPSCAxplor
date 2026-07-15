import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError } from "./api-client";
import type { QueryResponse, TokenResponse } from "./types";

const BASE = "http://api.test";

function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
  });
}

function tokens(accessToken: string): TokenResponse {
  return { access_token: accessToken, token_type: "bearer", expires_in: 900 };
}

const QUERY_RESPONSE: QueryResponse = {
  answer: "Overtime is paid at double time.",
  citations: [],
  model_used: "claude-haiku",
  disclaimer: "This answer is for reference only and does not constitute legal advice.",
  query_log_id: "log-1",
};

describe("ApiClient", () => {
  let client: ApiClient;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    client = new ApiClient(BASE);
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("login", () => {
    it("POSTs credentials with cookies and stores the access token in memory", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(200, tokens("jwt-1")));

      const result = await client.login("user@example.com", "hunter22");

      expect(result.access_token).toBe("jwt-1");
      expect(client.getAccessToken()).toBe("jwt-1");
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe(`${BASE}/auth/login`);
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
      expect(JSON.parse(init.body)).toEqual({
        email: "user@example.com",
        password: "hunter22",
      });
    });

    it("throws ApiError with the backend detail on bad credentials", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }));

      const error = await client.login("user@example.com", "wrong").catch((e) => e);

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(401);
      expect(error.detail).toBe("unauthorized");
      expect(client.getAccessToken()).toBeNull();
      // a failed login must not trigger the silent-refresh retry
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("refresh", () => {
    it("POSTs to /auth/refresh with cookies and updates the token", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse(200, tokens("jwt-2")));

      const result = await client.refresh();

      expect(result.access_token).toBe("jwt-2");
      expect(client.getAccessToken()).toBe("jwt-2");
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe(`${BASE}/auth/refresh`);
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
      expect(init.body).toBeUndefined();
    });

    it("clears the token and throws when the refresh cookie is invalid", async () => {
      client.setAccessToken("stale");
      fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }));

      await expect(client.refresh()).rejects.toBeInstanceOf(ApiError);
      expect(client.getAccessToken()).toBeNull();
    });

    it("dedupes concurrent refresh calls into one request", async () => {
      let release!: (r: Response) => void;
      fetchMock.mockReturnValueOnce(new Promise<Response>((r) => (release = r)));

      const first = client.refresh();
      const second = client.refresh();
      release(jsonResponse(200, tokens("jwt-3")));

      const [a, b] = await Promise.all([first, second]);
      expect(a.access_token).toBe("jwt-3");
      expect(b.access_token).toBe("jwt-3");
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe("logout", () => {
    it("POSTs to /auth/logout and clears the in-memory token", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(jsonResponse(204));

      await client.logout();

      expect(client.getAccessToken()).toBeNull();
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe(`${BASE}/auth/logout`);
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
    });

    it("clears the token even if the request fails", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(jsonResponse(500, { detail: "boom" }));

      await expect(client.logout()).rejects.toBeInstanceOf(ApiError);
      expect(client.getAccessToken()).toBeNull();
    });
  });

  describe("query", () => {
    it("sends the bearer token and cookies, returns the flat envelope", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(jsonResponse(200, QUERY_RESPONSE));

      const result = await client.query("What is the overtime rate?");

      expect(result).toEqual(QUERY_RESPONSE);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe(`${BASE}/query`);
      expect(init.method).toBe("POST");
      expect(init.credentials).toBe("include");
      expect(init.headers.Authorization).toBe("Bearer jwt-1");
      expect(JSON.parse(init.body)).toEqual({ query: "What is the overtime rate?" });
    });

    it("on 401, silently refreshes then retries once with the new token", async () => {
      client.setAccessToken("expired");
      fetchMock
        .mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }))
        .mockResolvedValueOnce(jsonResponse(200, tokens("jwt-new")))
        .mockResolvedValueOnce(jsonResponse(200, QUERY_RESPONSE));

      const result = await client.query("What is the overtime rate?");

      expect(result).toEqual(QUERY_RESPONSE);
      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(fetchMock.mock.calls[1][0]).toBe(`${BASE}/auth/refresh`);
      expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer jwt-new");
    });

    it("throws when the refresh itself fails, without retrying the original request", async () => {
      client.setAccessToken("expired");
      fetchMock
        .mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }))
        .mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }));

      const error = await client.query("anything").catch((e) => e);

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(401);
      expect(client.getAccessToken()).toBeNull();
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("does not refresh more than once per request (no retry loop)", async () => {
      client.setAccessToken("expired");
      fetchMock
        .mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }))
        .mockResolvedValueOnce(jsonResponse(200, tokens("jwt-new")))
        .mockResolvedValueOnce(jsonResponse(401, { detail: "unauthorized" }));

      const error = await client.query("anything").catch((e) => e);

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(401);
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it("surfaces rate-limit errors with status 429", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(
        jsonResponse(429, { detail: "monthly query limit reached" }),
      );

      const error = await client.query("anything").catch((e) => e);

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(429);
      expect(error.detail).toBe("monthly query limit reached");
    });
  });

  describe("listDocuments", () => {
    it("GETs /documents without a query string when no filters are given", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(jsonResponse(200, { documents: [], total: 0 }));

      await client.listDocuments();

      expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/documents`);
    });

    it("serializes filters, including is_expired=false", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(jsonResponse(200, { documents: [], total: 0 }));

      await client.listDocuments({
        union_name: "IBEW",
        document_type: "collective_agreement",
        is_expired: false,
      });

      const url = new URL(fetchMock.mock.calls[0][0]);
      expect(url.pathname).toBe("/documents");
      expect(url.searchParams.get("union_name")).toBe("IBEW");
      expect(url.searchParams.get("document_type")).toBe("collective_agreement");
      expect(url.searchParams.get("is_expired")).toBe("false");
    });
  });

  describe("getQueryHistory", () => {
    it("serializes limit and offset", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(
        jsonResponse(200, { queries: [], total: 0, limit: 10, offset: 20 }),
      );

      await client.getQueryHistory({ limit: 10, offset: 20 });

      const url = new URL(fetchMock.mock.calls[0][0]);
      expect(url.pathname).toBe("/query-history");
      expect(url.searchParams.get("limit")).toBe("10");
      expect(url.searchParams.get("offset")).toBe("20");
    });
  });

  describe("error handling", () => {
    it("falls back to a generic detail when the error body is not JSON", async () => {
      client.setAccessToken("jwt-1");
      fetchMock.mockResolvedValueOnce(new Response("gateway timeout", { status: 504 }));

      const error = await client.query("anything").catch((e) => e);

      expect(error).toBeInstanceOf(ApiError);
      expect(error.status).toBe(504);
      expect(typeof error.detail).toBe("string");
      expect(error.detail.length).toBeGreaterThan(0);
    });
  });
});
