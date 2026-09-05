"""Structured logging setup (loguru) + request-id correlation."""
import sys
import uuid
from contextvars import ContextVar

from loguru import logger

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    request_id_ctx.set(rid)
    return rid


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "rid={extra[rid]} | <cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}"
        ),
    )
    logger.add(
        "storage/logs/app.log",
        rotation="10 MB",
        retention="14 days",
        level="INFO",
        enqueue=True,
    )
    logger.configure(patcher=lambda rec: rec["extra"].update(rid=request_id_ctx.get()))