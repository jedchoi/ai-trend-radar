"""앱 조립 (logical-components.md: App). 실행: uvicorn app.main:app"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import logging_setup
from app.config import Settings
from app.i18n import Localizer
from app.middleware import GuardMiddleware, RateLimiter
from app.repository import Repository
from app.routes_ingest import router as ingest_router
from app.routes_public import router as public_router
from app.trends import TrendService

ERROR_CODES = {
    401: "unauthorized",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    422: "invalid_request",
    429: "rate_limited",
    503: "unavailable",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging_setup.configure()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.repo.init()
        try:
            yield
        finally:
            app.state.repo.close()

    app = FastAPI(
        title="AI Trend Radar API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    app.state.repo = Repository(settings.database_url, pool_size=settings.db_pool_size)
    app.state.trends = TrendService(app.state.repo)
    app.state.i18n = Localizer(app.state.repo)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse({"error": ERROR_CODES.get(exc.status_code, "http_error")}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # BR-S04: 입력 값 · 내부 정보는 빼고 위치만 알려준다
        fields = sorted({".".join(str(p) for p in err.get("loc", ())) for err in exc.errors()})[:20]
        return JSONResponse({"error": "invalid_request", "fields": fields}, status_code=422)

    app.include_router(public_router)
    app.include_router(ingest_router)
    app.add_middleware(
        GuardMiddleware,
        limiter=RateLimiter({"public": settings.public_rate_per_min, "ingest": settings.ingest_rate_per_min}),
        max_body_bytes=settings.max_body_bytes,
    )
    return app


def __getattr__(name: str):
    # `uvicorn app.main:app` 일 때만 환경 변수로 앱을 만든다 (테스트 import 시 부작용 없음)
    if name == "app":
        return create_app()
    raise AttributeError(name)
