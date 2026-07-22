from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings, get_settings
from src.routes.auth import router as auth_router
from src.routes.documents import router as documents_router
from src.routes.health import router as health_router
from src.routes.history import router as history_router
from src.routes.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Belt-and-suspenders: create_app() already resolves get_settings() at import
    # time, so a misconfigured env fails at process boot. This re-check at ASGI
    # startup is an lru_cache hit, not a second Settings() construction.
    get_settings()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    ``settings`` defaults to ``get_settings()`` resolved *by name at call time*
    (never captured), so tests and conftest can ``patch("src.main.get_settings")``
    and have the override honoured. CORS ``allow_origins`` is read from
    ``settings.cors_origins_list`` — the SAME single source the #104 CSRF gate
    uses — so the two controls cannot drift (#146).
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(title="EPSCAxplor API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
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

    return app


app = create_app()
