"""Health & readiness controller."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "app": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "time": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", summary="Readiness probe (checks DB + vector store)")
def ready(db: Session = Depends(get_db)):
    checks = {"database": "down", "vector_store": "down"}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception:
        pass
    try:
        from app.rag.vectorstore import get_collection
        checks["vector_store"] = f"up ({get_collection().count()} chunks)"
    except Exception:
        pass
    return {"status": "ready" if all(v != "down" for v in checks.values()) else "degraded",
            "checks": checks}