"""Tests for the per-surface Content-Security-Policy middleware (#156).

The API serves JSON on every path except Swagger UI (``/docs``) and ReDoc
(``/redoc``). These tests prove a strict ``default-src 'none'`` policy is
attached to every response (including errors and the schema), while ``/docs``
and ``/redoc`` receive a scoped relaxed policy that keeps their CDN-hosted
assets + inline bootstrap working. CSP is authored per-surface (not in the
shared Traefik header middleware) because the web app and the API need
different policies — #146 deferred CSP to #156. This API half ships *enforced*
(not Report-Only) because the policies are deterministic and covered here.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi.testclient import TestClient

from src.config import Settings
from src.csp import (
    ContentSecurityPolicyMiddleware,
    csp_for_path,
    docs_csp,
    strict_csp,
)
from src.main import create_app

STRICT = "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"


# --- builder units -----------------------------------------------------------


def test_strict_csp_exact() -> None:
    assert strict_csp() == STRICT


def test_docs_csp_allows_jsdelivr_cdn_for_every_asset_kind() -> None:
    policy = docs_csp()
    assert "https://cdn.jsdelivr.net" in policy
    # Swagger UI + ReDoc load their bundle, stylesheet, images and fonts from the
    # jsDelivr CDN, so the CDN must be allow-listed in each of those directives.
    for directive in ("script-src", "style-src", "img-src", "font-src"):
        assert "https://cdn.jsdelivr.net" in _directive(policy, directive), directive


def test_docs_csp_allows_inline_bootstrap() -> None:
    policy = docs_csp()
    # Swagger UI + ReDoc inject an inline bootstrap <script> and inline <style>.
    assert "'unsafe-inline'" in _directive(policy, "script-src")
    assert "'unsafe-inline'" in _directive(policy, "style-src")


def test_docs_csp_img_allows_data_and_fastapi_favicon() -> None:
    img = _directive(docs_csp(), "img-src")
    assert "data:" in img
    assert "https://fastapi.tiangolo.com" in img


def test_docs_csp_allows_redoc_blob_worker() -> None:
    # ReDoc builds its search index inside a blob: web worker.
    assert "worker-src 'self' blob:" in docs_csp()


def test_docs_csp_allows_redoc_google_fonts() -> None:
    # ReDoc's stock page links a Google Fonts stylesheet (googleapis) whose
    # @font-face rules load the font files from a second host (gstatic).
    policy = docs_csp()
    assert "https://fonts.googleapis.com" in _directive(policy, "style-src")
    assert "https://fonts.gstatic.com" in _directive(policy, "font-src")


def test_docs_csp_keeps_frame_ancestors_and_default_locked() -> None:
    # Consistent with the shipped X-Frame-Options: DENY (#146); default stays none.
    assert "frame-ancestors 'none'" in docs_csp()
    assert "default-src 'none'" in docs_csp()


def test_csp_for_path_routes_docs_uis_to_relaxed_policy() -> None:
    assert csp_for_path("/docs") == docs_csp()
    assert csp_for_path("/redoc") == docs_csp()


def test_csp_for_path_defaults_to_strict_with_exact_match() -> None:
    # Exact-path match only — JSON, the schema, and near-miss prefixes are strict.
    for path in ("/query", "/health", "/openapi.json", "/", "/docsomething", "/docs/extra"):
        assert csp_for_path(path) == strict_csp(), path


# --- integration via the app's middleware stack ------------------------------


def test_middleware_registered_by_create_app() -> None:
    app = create_app(_settings())
    assert any(
        m.cls is ContentSecurityPolicyMiddleware for m in app.user_middleware
    ), "ContentSecurityPolicyMiddleware is not configured on the app"


def test_health_response_carries_strict_csp(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.headers["content-security-policy"] == STRICT


def test_unknown_path_still_carries_strict_csp(client: TestClient) -> None:
    # Middleware wraps the whole stack, so even a 404 gets a policy.
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    assert resp.headers["content-security-policy"] == STRICT


def test_openapi_schema_is_strict(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.headers["content-security-policy"] == STRICT


def test_docs_renders_with_relaxed_csp(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200  # Swagger UI still served
    assert resp.headers["content-security-policy"] == docs_csp()


def test_redoc_renders_with_relaxed_csp(client: TestClient) -> None:
    resp = client.get("/redoc")
    assert resp.status_code == 200  # ReDoc still served
    assert resp.headers["content-security-policy"] == docs_csp()


def test_docs_html_external_hosts_are_covered_by_policy(client: TestClient) -> None:
    # Regression guard: every external https:// host the served Swagger/ReDoc
    # HTML references must be allow-listed by the docs policy, so a future
    # FastAPI bump that swaps a CDN/font host cannot silently break the docs
    # under enforcement. (Font *files* pulled transitively by the Google Fonts
    # stylesheet are covered by font-src but never appear in the HTML, so they
    # are legitimately out of this scan's scope.)
    policy = docs_csp()
    for path in ("/docs", "/redoc"):
        hosts = _external_hosts(client.get(path).text)
        assert hosts, f"expected external asset hosts in {path} HTML"
        for host in hosts:
            assert host in policy, f"{host} referenced by {path} is not in the docs CSP"


# --- helpers -----------------------------------------------------------------


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="csp-test-secret",
    )
    base.update(overrides)
    return Settings(**base)


def _directive(policy: str, name: str) -> str:
    """Return the single ``name ...`` directive segment from a CSP string."""
    for raw in policy.split(";"):
        segment = raw.strip()
        if segment.split(" ", 1)[0] == name:
            return segment
    raise AssertionError(f"directive {name!r} not found in policy: {policy!r}")


_EXTERNAL_HOST = re.compile(r"https://([a-z0-9.-]+)")


def _external_hosts(html: str) -> set[str]:
    """Distinct ``https://`` hostnames referenced by an HTML document."""
    return {match.group(1) for match in _EXTERNAL_HOST.finditer(html)}
