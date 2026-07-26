"""Settings parsing tests.

Focused coverage for the optional ``qdrant_read_only_api_key`` field (#155):
the API reads Qdrant with a least-privilege read-only key, so the field must
parse from ``QDRANT_READ_ONLY_API_KEY`` when set, default to ``None`` when
unset, and normalize a blank value to ``None`` so an empty
``${QDRANT_READ_ONLY_API_KEY}`` (what an unset compose var expands to) never
becomes an empty ``api-key`` header on the wire. The write-capable
``QDRANT_API_KEY`` is deliberately NOT a field on the API Settings (only
ingestion/backups hold it), so the API cannot forward a write key.
"""

import pytest

from src.config import Settings

# Minimal set of otherwise-required env vars so ``Settings()`` constructs.
REQUIRED_ENV = {
    "DATABASE_URL": "postgresql://user:pass@localhost/epsca",
    "QDRANT_URL": "http://localhost:6333",
    "OLLAMA_URL": "http://localhost:11434",
    "ANTHROPIC_API_KEY": "test-key",
    "JWT_SECRET": "test-jwt-secret",
}


def _set_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


class TestQdrantReadOnlyApiKeySetting:
    def test_parsed_from_env_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_READ_ONLY_API_KEY", "reader-secret-key")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_read_only_api_key == "reader-secret-key"

    def test_defaults_to_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.delenv("QDRANT_READ_ONLY_API_KEY", raising=False)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_read_only_api_key is None

    def test_empty_string_normalized_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_READ_ONLY_API_KEY", "")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_read_only_api_key is None

    def test_whitespace_only_normalized_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_READ_ONLY_API_KEY", "   ")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_read_only_api_key is None

    def test_real_key_is_not_altered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A real key must pass through byte-for-byte so the client and the
        # Qdrant service (reading QDRANT__SERVICE__READ_ONLY_API_KEY) stay matched.
        key = "  spaced-but-real  "
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_READ_ONLY_API_KEY", key)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_read_only_api_key == key

    def test_write_key_field_is_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Least-privilege (#155): the write-capable key must NOT be a field on
        # the API Settings, so the query path cannot forward it even if the env
        # var is present on the container.
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_API_KEY", "write-capable-key")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert not hasattr(settings, "qdrant_api_key")


class TestCorsOriginsList:
    """The single normalized CORS/CSRF allow-list parser (#146).

    ``cors_origins_list`` is the one source of truth consumed by both the
    CORSMiddleware (main.py) and the #104 CSRF Origin gate (auth.py). Its
    normalization must match the old ``_allowed_origins`` exactly — strip,
    drop a trailing slash, lowercase, skip empty entries — so the swap is
    behaviour-preserving and the two layers can never drift apart.
    """

    def test_single_origin_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example"]

    def test_multiple_origins_split_on_comma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example,https://b.example")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example", "https://b.example"]

    def test_strips_surrounding_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", " https://a.example , https://b.example ")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example", "https://b.example"]

    def test_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example/")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example"]

    def test_lowercases_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "HTTPS://A.EXAMPLE")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example"]

    def test_skips_empty_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "https://a.example,,  ,https://b.example")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example", "https://b.example"]

    def test_default_value_parses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["http://localhost:3000"]

    def test_combined_normalization(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", " HTTPS://A.EXAMPLE/ ,, https://B.example ")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.cors_origins_list == ["https://a.example", "https://b.example"]

    def test_empty_or_separator_only_yields_empty_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An empty or all-separator CORS_ORIGINS produces an empty allow-list,
        # which fails CLOSED: CORSMiddleware allows no origin and the #104 CSRF
        # gate rejects every cross-site request (it is never treated as a wildcard).
        _set_required(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "")
        assert Settings(_env_file=None).cors_origins_list == []  # type: ignore[call-arg]
        monkeypatch.setenv("CORS_ORIGINS", ",,  ,")
        assert Settings(_env_file=None).cors_origins_list == []  # type: ignore[call-arg]
