"""GET /query-history — the authenticated tenant's past queries (#26).

Tenant-scoped: results are restricted to ``current_user.tenant_id`` so one tenant
can never see another's history (the Phase 3 multi-tenant isolation requirement).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.auth import CurrentUser, get_current_user
from src.config import Settings, get_settings
from src.db import connect
from src.db.query_logs import count_query_logs, list_query_logs

router = APIRouter()


class QueryHistoryItem(BaseModel):
    id: str
    query_text: str
    answer: str
    model_used: str
    citations: list[dict[str, Any]]
    created_at: datetime


class QueryHistoryResponse(BaseModel):
    queries: list[QueryHistoryItem]
    total: int
    limit: int
    offset: int


@router.get("/query-history", response_model=QueryHistoryResponse)
async def query_history_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QueryHistoryResponse:
    """Return the caller's tenant query history, newest first, paginated."""
    async with connect(settings.database_url) as conn:
        records = await list_query_logs(
            conn, current_user.tenant_id, limit=limit, offset=offset
        )
        total = await count_query_logs(conn, current_user.tenant_id)
    queries = [
        QueryHistoryItem(
            id=str(r.id),
            query_text=r.query_text,
            answer=r.response_text,
            model_used=r.model_used,
            citations=r.citations,
            created_at=r.created_at,
        )
        for r in records
    ]
    return QueryHistoryResponse(queries=queries, total=total, limit=limit, offset=offset)
