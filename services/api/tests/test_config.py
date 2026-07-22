"""Settings parsing tests.

Focused coverage for the optional ``qdrant_api_key`` field (#144): it must
parse from the environment when set, default to ``None`` when unset, and
normalize a blank value to ``None`` so an empty ``QDRANT_API_KEY`` (what an
unset ``${QDRANT_API_KEY}`` compose var expands to) never becomes an empty
``api-key`` header on the wire.
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


class TestQdrantApiKeySetting:
    def test_parsed_from_env_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_API_KEY", "super-secret-key")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_api_key == "super-secret-key"

    def test_defaults_to_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.delenv("QDRANT_API_KEY", raising=False)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_api_key is None

    def test_empty_string_normalized_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_API_KEY", "")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_api_key is None

    def test_whitespace_only_normalized_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_API_KEY", "   ")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_api_key is None

    def test_real_key_is_not_altered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A real key must pass through byte-for-byte so the client and the
        # Qdrant service (both reading the same ${QDRANT_API_KEY}) stay matched.
        key = "  spaced-but-real  "
        _set_required(monkeypatch)
        monkeypatch.setenv("QDRANT_API_KEY", key)
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.qdrant_api_key == key
