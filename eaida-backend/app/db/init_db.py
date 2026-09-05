"""Create tables and bootstrap the first admin user."""
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import dataset, document, job, user  # noqa: F401  (register metadata)
from app.models.user import User, UserRole


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
        if not existing:
            admin = User(
                email=settings.FIRST_ADMIN_EMAIL,
                full_name="System Admin",
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Bootstrapped admin user: {settings.FIRST_ADMIN_EMAIL}")
    finally:
        db.close()