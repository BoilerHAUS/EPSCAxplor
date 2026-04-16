import asyncio
from typing import Annotated, Literal

import asyncpg
import httpx
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from src.config import Settings, get_settings

router = APIRouter()

HealthStatus = Literal["ok", "error"]


class DependencyStatuses(BaseModel):
    database: HealthStatus
    qdrant: HealthStatus
    ollama: HealthStatus


class HealthResponse(BaseModel):
    status: HealthStatus
    dependencies: DependencyStatuses


async def _check_database(database_url: str) -> HealthStatus:
    conn = None
    try:
        conn = await asyncpg.connect(database_url, timeout=5)
        await conn.execute("SELECT 1")
        return "ok"
    except Exception:  # noqa: BLE001
        return "error"
    finally:
        if conn is not None:
            await conn.close()


async def _check_qdrant(qdrant_url: str) -> HealthStatus:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{qdrant_url}/healthz")
            return "ok" if response.status_code == 200 else "error"
    except Exception:  # noqa: BLE001
        return "error"


async def _check_ollama(ollama_url: str) -> HealthStatus:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            return "ok" if response.status_code == 200 else "error"
    except Exception:  # noqa: BLE001
        return "error"


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
async def health(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    database_status, qdrant_status, ollama_status = await asyncio.gather(
        _check_database(settings.database_url),
        _check_qdrant(settings.qdrant_url),
        _check_ollama(settings.ollama_url),
    )

    all_ok = database_status == "ok" and qdrant_status == "ok" and ollama_status == "ok"

    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if all_ok else "error",
        dependencies=DependencyStatuses(
            database=database_status,
            qdrant=qdrant_status,
            ollama=ollama_status,
        ),
    )
