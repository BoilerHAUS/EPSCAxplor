"""Per-surface Content-Security-Policy for the API (#156).

The four simple security headers (HSTS, ``X-Content-Type-Options``,
``Referrer-Policy``, ``X-Frame-Options``) ship via a shared Traefik middleware
(#146/#159). CSP was deferred to this issue because one Traefik-wide string
cannot cover both the Next.js web app and this API's Swagger UI at once — so CSP
is authored per-surface, in each app.

This API serves JSON on every path except Swagger UI (``/docs``) and ReDoc
(``/redoc``). JSON responses need no content sources, so every non-docs path
gets a strict ``default-src 'none'`` policy — harmless on JSON, protective on
any incidental HTML/error page. ``/docs`` and ``/redoc`` get a scoped relaxed
policy allowing exactly what Swagger UI / ReDoc need: their bundle from the
jsDelivr CDN, an inline bootstrap script + style, ``data:``/favicon images,
ReDoc's Google-hosted fonts (its stock page links ``fonts.googleapis.com`` for
the stylesheet and pulls the font files from ``fonts.gstatic.com``), and (for
ReDoc) a ``blob:`` web worker. Both keep ``frame-ancestors 'none'`` to stay
consistent with the shipped ``X-Frame-Options: DENY``.

This surface ships *enforced* (not Report-Only): the policies are deterministic
and covered by tests, so there is no observation ramp to run — unlike the web
surface, whose hydration/inline needs warrant a Report-Only ramp.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# jsDelivr hosts the Swagger UI bundle + ReDoc standalone bundle that FastAPI
# references by default; the FastAPI favicon is served from its own site.
_CDN = "https://cdn.jsdelivr.net"
_FAVICON_HOST = "https://fastapi.tiangolo.com"
# ReDoc's stock page links a Google Fonts stylesheet (googleapis) whose @font-face
# rules load the font files from a second host (gstatic).
_FONTS_CSS_HOST = "https://fonts.googleapis.com"
_FONTS_FILE_HOST = "https://fonts.gstatic.com"

# Paths that render interactive HTML docs and therefore need the relaxed policy.
# Exact-match only: a near-miss like "/docs/oauth2-redirect" or "/docsomething"
# must fall through to the strict policy rather than inherit the CDN allowances.
_DOCS_PATHS = frozenset({"/docs", "/redoc"})

_STRICT_CSP = "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"

_DOCS_CSP = (
    "default-src 'none'; "
    f"script-src 'self' 'unsafe-inline' {_CDN}; "
    f"style-src 'self' 'unsafe-inline' {_CDN} {_FONTS_CSS_HOST}; "
    f"img-src 'self' data: {_CDN} {_FAVICON_HOST}; "
    f"font-src 'self' {_CDN} {_FONTS_FILE_HOST}; "
    "worker-src 'self' blob:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'"
)


def strict_csp() -> str:
    """Strict policy for JSON/error responses — no content sources at all."""
    return _STRICT_CSP


def docs_csp() -> str:
    """Relaxed policy scoped to Swagger UI (``/docs``) and ReDoc (``/redoc``)."""
    return _DOCS_CSP


def csp_for_path(path: str) -> str:
    """Return the CSP appropriate for ``path`` (relaxed only for the docs UIs)."""
    return docs_csp() if path in _DOCS_PATHS else strict_csp()


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """Attach a per-path ``Content-Security-Policy`` to every response.

    Wraps the whole application stack, so the policy is present on every
    response — including 404/422/500 error bodies and the Swagger/ReDoc HTML —
    leaving no surface without a policy.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = csp_for_path(request.url.path)
        return response
