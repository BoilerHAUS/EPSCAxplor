from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import Response

from src.config import Settings
from src.routes.health import _check_database, _check_ollama, _check_qdrant, health


class TestHealthEndpoint:
    async def test_all_dependencies_ok_returns_200(self, test_settings: Settings) -> None:
        with (
            patch("src.routes.health._check_database", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_qdrant", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_ollama", new=AsyncMock(return_value="ok")),
        ):
            response_state = Response()
            payload = await health(response_state, settings=test_settings)
        assert response_state.status_code == 200
        assert payload.model_dump() == {
            "status": "ok",
            "dependencies": {"database": "ok", "qdrant": "ok", "ollama": "ok"},
        }

    async def test_database_down_returns_503(self, test_settings: Settings) -> None:
        with (
            patch("src.routes.health._check_database", new=AsyncMock(return_value="error")),
            patch("src.routes.health._check_qdrant", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_ollama", new=AsyncMock(return_value="ok")),
        ):
            response_state = Response()
            payload = await health(response_state, settings=test_settings)
        assert response_state.status_code == 503
        data = payload.model_dump()
        assert data["status"] == "error"
        assert data["dependencies"]["database"] == "error"
        assert data["dependencies"]["qdrant"] == "ok"
        assert data["dependencies"]["ollama"] == "ok"

    async def test_qdrant_down_returns_503(self, test_settings: Settings) -> None:
        with (
            patch("src.routes.health._check_database", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_qdrant", new=AsyncMock(return_value="error")),
            patch("src.routes.health._check_ollama", new=AsyncMock(return_value="ok")),
        ):
            response_state = Response()
            payload = await health(response_state, settings=test_settings)
        assert response_state.status_code == 503
        data = payload.model_dump()
        assert data["status"] == "error"
        assert data["dependencies"]["qdrant"] == "error"

    async def test_ollama_down_returns_503(self, test_settings: Settings) -> None:
        with (
            patch("src.routes.health._check_database", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_qdrant", new=AsyncMock(return_value="ok")),
            patch("src.routes.health._check_ollama", new=AsyncMock(return_value="error")),
        ):
            response_state = Response()
            payload = await health(response_state, settings=test_settings)
        assert response_state.status_code == 503
        data = payload.model_dump()
        assert data["status"] == "error"
        assert data["dependencies"]["ollama"] == "error"

    async def test_all_dependencies_down_returns_503(self, test_settings: Settings) -> None:
        with (
            patch("src.routes.health._check_database", new=AsyncMock(return_value="error")),
            patch("src.routes.health._check_qdrant", new=AsyncMock(return_value="error")),
            patch("src.routes.health._check_ollama", new=AsyncMock(return_value="error")),
        ):
            response_state = Response()
            payload = await health(response_state, settings=test_settings)
        assert response_state.status_code == 503
        data = payload.model_dump()
        assert data["status"] == "error"
        assert all(v == "error" for v in data["dependencies"].values())


class TestCheckDatabase:
    async def test_ok_when_connection_succeeds(self) -> None:
        mock_conn = AsyncMock()
        with patch("src.routes.health.asyncpg.connect", new=AsyncMock(return_value=mock_conn)):
            result = await _check_database("postgresql://user:pass@localhost/epsca")
        assert result == "ok"
        mock_conn.execute.assert_called_once_with("SELECT 1")
        mock_conn.close.assert_called_once()

    async def test_error_when_connection_fails(self) -> None:
        with patch(
            "src.routes.health.asyncpg.connect",
            new=AsyncMock(side_effect=OSError("Connection refused")),
        ):
            result = await _check_database("postgresql://bad-host/epsca")
        assert result == "error"

    async def test_error_when_execute_fails(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = RuntimeError("query failed")
        with patch("src.routes.health.asyncpg.connect", new=AsyncMock(return_value=mock_conn)):
            result = await _check_database("postgresql://user:pass@localhost/epsca")
        assert result == "error"
        mock_conn.close.assert_called_once()  # connection must be closed even on failure


def _make_http_client_mock(
    status_code: int | None = None, error: Exception | None = None
) -> AsyncMock:
    """Build an AsyncMock for httpx.AsyncClient that correctly handles async with."""
    mock_response = MagicMock()
    mock_client = AsyncMock()
    # __aenter__ must return mock_client itself so client.get resolves correctly
    mock_client.__aenter__.return_value = mock_client
    if error is not None:
        mock_client.get.side_effect = error
    else:
        mock_response.status_code = status_code
        mock_client.get.return_value = mock_response
    return mock_client


class TestCheckQdrant:
    async def test_ok_when_healthz_returns_200(self) -> None:
        mock_client = _make_http_client_mock(status_code=200)
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_qdrant("http://localhost:6333")
        assert result == "ok"
        mock_client.get.assert_called_once_with("http://localhost:6333/healthz")

    async def test_error_when_healthz_returns_non_200(self) -> None:
        mock_client = _make_http_client_mock(status_code=503)
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_qdrant("http://localhost:6333")
        assert result == "error"

    async def test_error_when_connection_fails(self) -> None:
        mock_client = _make_http_client_mock(error=httpx.ConnectError("Connection failed"))
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_qdrant("http://bad-host:6333")
        assert result == "error"


class TestCheckOllama:
    async def test_ok_when_api_tags_returns_200(self) -> None:
        mock_client = _make_http_client_mock(status_code=200)
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_ollama("http://localhost:11434")
        assert result == "ok"
        mock_client.get.assert_called_once_with("http://localhost:11434/api/tags")

    async def test_error_when_api_tags_returns_non_200(self) -> None:
        mock_client = _make_http_client_mock(status_code=500)
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_ollama("http://localhost:11434")
        assert result == "error"

    async def test_error_when_connection_fails(self) -> None:
        mock_client = _make_http_client_mock(error=httpx.ConnectError("Connection failed"))
        with patch("src.routes.health.httpx.AsyncClient", return_value=mock_client):
            result = await _check_ollama("http://bad-host:11434")
        assert result == "error"
