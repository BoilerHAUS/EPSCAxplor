from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_settings()  # raises ValidationError immediately if env is misconfigured
    yield


app = FastAPI(title="EPSCAxplor API", lifespan=lifespan)

app.include_router(health_router)
