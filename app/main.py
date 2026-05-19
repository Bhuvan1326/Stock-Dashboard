"""FastAPI application entry point with startup ingestion and error handling."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.database import SessionLocal
from app.ingest import ingest_if_needed
from app.routes import compare, stocks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and ingest market data when the database is empty."""
    db = SessionLocal()
    try:
        ingest_if_needed(db)
    except Exception:
        logger.exception("Startup ingestion failed")
        raise
    finally:
        db.close()
    yield


app = FastAPI(
    title="Stock Data Intelligence Dashboard",
    description="Jarnox internship submission — NSE equity analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(compare.router)


@app.get("/", include_in_schema=False)
async def serve_dashboard() -> FileResponse:
    """Serve the single-page dashboard."""
    return FileResponse("frontend/index.html")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation failures in the same shape as other API errors."""
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request parameters"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Normalize HTTP errors to {error: message} for the frontend."""
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"error": message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return a safe JSON error instead of exposing stack traces to clients."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},
    )
