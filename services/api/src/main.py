import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.routes.auth import router as auth_router
from src.routes.documents import router as documents_router
from src.routes.health import router as health_router
from src.routes.history import router as history_router
from src.routes.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_settings()  # raises ValidationError immediately if env is misconfigured
    yield


app = FastAPI(title="EPSCAxplor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    # allow_credentials is required for the httpOnly refresh cookie to round-trip;
    # it is incompatible with a wildcard origin, so CORS_ORIGINS must list exact origins.
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(history_router)
