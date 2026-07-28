/**
 * Content-Security-Policy construction for the web app (#156).
 *
 * The CSP is emitted per request by `src/middleware.ts` with a fresh nonce, so
 * `script-src` is locked to `'nonce-…' 'strict-dynamic'` — no `'unsafe-inline'`
 * for scripts, the strong protection against injected/XSS scripts. Next.js
 * auto-applies the nonce to its own framework/bootstrap scripts, and the
 * theme-init inline script in `app/layout.tsx` carries it explicitly.
 *
 * `style-src` keeps `'unsafe-inline'` on purpose: the app uses inline `style={}`
 * attributes (which a nonce cannot cover) and `next/font` injects an inline
 * `<style>`. Inline styles are a far lower risk than inline scripts, which stay
 * strictly nonce-gated.
 *
 * Kept dependency-free and framework-free so it is unit-testable in isolation
 * (the thin middleware wrapper does the Next.js request/response plumbing).
 */

/** A fresh, unpredictable base64 nonce, using Web Crypto (Edge-runtime safe). */
export function generateNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  // btoa over the raw bytes — never Node's `Buffer`, which is not guaranteed in
  // the Edge runtime that Next.js middleware runs in.
  return btoa(String.fromCharCode(...bytes));
}

/**
 * Build the `connect-src` value. The web app fetches the API cross-origin at
 * `NEXT_PUBLIC_API_URL` (baked at build), so its origin must be allow-listed
 * or every fetch is blocked under enforcement. Mirrors `api-client.ts`, which
 * falls back to same-origin when the var is unset; a missing or malformed value
 * degrades to `'self'` and never throws (a throw here would 500 every request).
 */
export function deriveConnectSrc(apiUrl?: string): string {
  if (!apiUrl) {
    return "'self'";
  }
  try {
    return `'self' ${new URL(apiUrl).origin}`;
  } catch {
    return "'self'";
  }
}

export interface CspOptions {
  /** Per-request nonce from the middleware. */
  nonce: string;
  /** `NEXT_PUBLIC_API_URL`; its origin is added to `connect-src`. */
  apiUrl?: string;
  /** In dev React uses `eval` for error overlays, so `'unsafe-eval'` is added. */
  isDev?: boolean;
}

/** Build the full Content-Security-Policy header value for one request. */
export function buildCsp({ nonce, apiUrl, isDev = false }: CspOptions): string {
  // Production needs neither `'unsafe-eval'` nor `'unsafe-inline'` for scripts.
  const scriptSrc = [
    "script-src 'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    isDev ? "'unsafe-eval'" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self'",
    `connect-src ${deriveConnectSrc(apiUrl)}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
}
