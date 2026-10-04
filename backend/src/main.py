import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider
from dishka.integrations.fastapi import setup_dishka as setup_fastapi_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from src.admin.site import AdminSite
from src.api import router
from src.api.exc.handler import ApiErrorHandler
from src.config import cfg
from src.config.exc import ConfigIncompleteError
from src.core.di import (
    AccessProvider,
    AdminProvider,
    AuthProvider,
    CoursesProvider,
    DbProvider,
    MaterialsProvider,
    ProfileProvider,
    S3Provider,
    SecurityProvider,
)
from src.core.logging import setup_logging
from src.core.metrics import PrometheusMiddleware
from src.core.middleware import RequestLoggingMiddleware

log = logging.getLogger(__name__)

container = make_async_container(
    FastapiProvider(),
    DbProvider(),
    SecurityProvider(),
    AuthProvider(),
    AdminProvider(),
    AccessProvider(),
    CoursesProvider(),
    S3Provider(),
    MaterialsProvider(),
    ProfileProvider(),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(cfg.logging.level)
    if missing := cfg.missing_required():
        log.critical("app.config_incomplete", extra={"missing_settings": missing})
        raise ConfigIncompleteError({"missing_settings": missing})
    try:
        yield
    finally:
        await container.close()


app = FastAPI(
    title="Labka",
    lifespan=lifespan,
)

setup_fastapi_dishka(app=app, container=container)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors.origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(router)

ApiErrorHandler.register(app)
AdminSite.mount(app)


@app.get("/")
async def ping() -> dict[str, str]:
    return {"ping": "pong"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, log_config=None, workers=1)


if __name__ == "__main__":
    main()
