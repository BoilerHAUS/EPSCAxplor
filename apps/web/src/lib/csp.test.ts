import { describe, expect, it } from "vitest";
import { buildCsp, deriveConnectSrc, generateNonce } from "./csp";

const BASE64 = /^[A-Za-z0-9+/]+=*$/;

describe("generateNonce", () => {
  it("returns a non-empty base64 string", () => {
    const nonce = generateNonce();
    expect(nonce.length).toBeGreaterThan(0);
    expect(nonce).toMatch(BASE64);
  });

  it("returns a different value on each call", () => {
    expect(generateNonce()).not.toBe(generateNonce());
  });

  it("only ever emits base64 characters (no hex/Buffer leak)", () => {
    for (let i = 0; i < 25; i += 1) {
      expect(generateNonce()).toMatch(BASE64);
    }
  });
});

describe("deriveConnectSrc", () => {
  it("allow-lists the API origin alongside 'self'", () => {
    expect(deriveConnectSrc("https://api.epscaxplor.com")).toBe(
      "'self' https://api.epscaxplor.com",
    );
  });

  it("strips any path/query down to the bare origin", () => {
    expect(deriveConnectSrc("https://api.epscaxplor.com/v1/query?x=1")).toBe(
      "'self' https://api.epscaxplor.com",
    );
  });

  it("falls back to 'self' when the URL is unset or empty (dev/same-origin)", () => {
    expect(deriveConnectSrc(undefined)).toBe("'self'");
    expect(deriveConnectSrc("")).toBe("'self'");
  });

  it("degrades to 'self' on a malformed URL instead of throwing", () => {
    expect(() => deriveConnectSrc("not a url")).not.toThrow();
    expect(deriveConnectSrc("not a url")).toBe("'self'");
  });
});

describe("buildCsp", () => {
  const nonce = "test-nonce-123";

  it("includes the hardened baseline directives", () => {
    const csp = buildCsp({ nonce });
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("form-action 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("upgrade-insecure-requests");
  });

  it("locks script-src to the request nonce with strict-dynamic", () => {
    expect(buildCsp({ nonce })).toContain(
      `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    );
  });

  it("keeps style-src 'unsafe-inline' for inline style attrs + next/font", () => {
    expect(buildCsp({ nonce })).toContain("style-src 'self' 'unsafe-inline'");
  });

  it("never allows 'unsafe-inline' in script-src, even in dev", () => {
    const scriptSrc = directive(buildCsp({ nonce, isDev: true }), "script-src");
    expect(scriptSrc).not.toContain("'unsafe-inline'");
  });

  it("adds 'unsafe-eval' only in development", () => {
    expect(buildCsp({ nonce, isDev: true })).toContain("'unsafe-eval'");
    expect(buildCsp({ nonce, isDev: false })).not.toContain("'unsafe-eval'");
  });

  it("sets img-src and font-src for the self-hosted fonts", () => {
    const csp = buildCsp({ nonce });
    expect(csp).toContain("img-src 'self' blob: data:");
    expect(csp).toContain("font-src 'self'");
  });

  it("embeds the derived connect-src for the cross-origin API", () => {
    expect(buildCsp({ nonce, apiUrl: "https://api.epscaxplor.com" })).toContain(
      "connect-src 'self' https://api.epscaxplor.com",
    );
  });
});

function directive(csp: string, name: string): string {
  const found = csp
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.split(" ", 1)[0] === name);
  if (found === undefined) {
    throw new Error(`directive ${name} not found in: ${csp}`);
  }
  return found;
}
