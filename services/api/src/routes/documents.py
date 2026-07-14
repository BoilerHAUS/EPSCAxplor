"""GET /documents — corpus registry listing (#26).

The corpus is shared across tenants, so this is not tenant-scoped; auth is still
required (a valid credential), enforced by the route-level dependency.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth import get_current_user
from src.config import Settings, get_settings
from src.db import connect
from src.db.documents import list_documents

router = APIRouter()


class DocumentItem(BaseModel):
    id: str
    union_name: str
    document_type: str
    title: str
    effective_date: date | None
    expiry_date: date | None
    is_expired: bool
    chunk_count: int | None
    ingested_at: datetime | None


class DocumentsResponse(BaseModel):
    documents: list[DocumentItem]
    total: int


@router.get(
    "/documents",
    response_model=DocumentsResponse,
    dependencies=[Depends(get_current_user)],
)
async def list_documents_route(
    settings: Annotated[Settings, Depends(get_settings)],
    union_name: str | None = None,
    document_type: str | None = None,
    is_expired: bool | None = None,
) -> DocumentsResponse:
    """List corpus documents, optionally filtered by union / type / expiry."""
    async with connect(settings.database_url) as conn:
        records = await list_documents(
            conn,
            union_name=union_name,
            document_type=document_type,
            is_expired=is_expired,
        )
    items = [
        DocumentItem(
            id=str(r.id),
            union_name=r.union_name,
            document_type=r.document_type,
            title=r.title,
            effective_date=r.effective_date,
            expiry_date=r.expiry_date,
            is_expired=r.is_expired,
            chunk_count=r.chunk_count,
            ingested_at=r.ingested_at,
        )
        for r in records
    ]
    return DocumentsResponse(documents=items, total=len(items))
