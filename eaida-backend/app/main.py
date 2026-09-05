"""Enterprise AI Data Analyst - FastAPI application entrypoint."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, new_request_id
from app.db.init_db import init_db

DESCRIPTION = """
**Enterprise AI Data Analyst** - an LLM-powered analytics platform.

Capabilities: AutoML, feature engineering, data profiling, model comparison,
explainability (SHAP), automated reporting, hybrid RAG over an enterprise
knowledge base, and a multi-agent analysis workflow.

**Roles:** `admin` (everything) - `analyst` (upload + run analyses) - `viewer` (read-only).
Click **Authorize** and log in with your email + password to try the endpoints.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} [{settings.ENVIRONMENT}]")
    init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    rid = new_request_id()
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Process-Time-ms"] = str(duration_ms)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} "
                f"({duration_ms} ms)")
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(status_code=500,
                        content={"detail": "Internal server error", "path": request.url.path})


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"], summary="Service root")
def root():
    return {"service": settings.APP_NAME, "version": "1.0.0",
            "docs": "/docs", "api": settings.API_V1_PREFIX}