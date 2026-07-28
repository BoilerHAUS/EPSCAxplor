import { type NextRequest, NextResponse } from "next/server";
import { buildCsp, generateNonce } from "@/lib/csp";

/**
 * Emit a per-request, nonce-based Content-Security-Policy (#156).
 *
 * The *response* header is `Content-Security-Policy` (enforcing). The policy was
 * verified violation-free (every script nonced, no un-nonced inline styles/scripts)
 * before enabling enforcement. ROLLBACK LEVER: if an unforeseen violation breaks a
 * page in production, flip `RESPONSE_CSP_HEADER` back to
 * `"Content-Security-Policy-Report-Only"` and redeploy — the policy then only
 * reports (breaking nothing) while you diagnose.
 *
 * The *request* header is ALWAYS the enforce name `Content-Security-Policy`,
 * because Next.js only auto-applies the nonce to its own framework/bootstrap
 * scripts when it reads the nonce from a request header spelled exactly that.
 * Using the `-Report-Only` name on the request would leave framework scripts
 * un-nonced and flood the report with false violations.
 */

// ROLLBACK: set to "Content-Security-Policy-Report-Only" to report without enforcing.
const RESPONSE_CSP_HEADER = "Content-Security-Policy";

export function middleware(request: NextRequest): NextResponse {
  const nonce = generateNonce();
  const csp = buildCsp({
    nonce,
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
    isDev: process.env.NODE_ENV === "development",
  });

  // Next.js reads the nonce from the request CSP header (enforce name) to nonce
  // its own scripts; `x-nonce` lets the root layout apply the same nonce to the
  // inline theme-init script.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set(RESPONSE_CSP_HEADER, csp);
  return response;
}

export const config = {
  matcher: [
    /*
     * Run on all document requests, but skip paths that render no HTML and need
     * no nonce'd CSP:
     * - api            (no same-origin API routes; the API is a separate origin)
     * - _next/static   (build JS/CSS)
     * - _next/image    (image optimizer)
     * - favicon.ico    (static asset)
     * Also skip `next/link` prefetches, which don't render the page.
     */
    {
      source: "/((?!api|_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
