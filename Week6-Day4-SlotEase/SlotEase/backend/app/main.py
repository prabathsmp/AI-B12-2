import logging
import time

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import Base, SessionLocal, engine
from .errors import AppError, app_error_handler, validation_error_handler
from .routers import ai, auth, owner, public
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("slotease")

app = FastAPI(
    title="SlotEase API",
    version="1.0.0",
    description="Multi-tenant appointment booking for clinics and salons.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(owner.router)
app.include_router(ai.router)


@app.on_event("startup")
def startup() -> None:
    for attempt in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as exc:  # noqa: BLE001
            log.info("Waiting for database (%s/30): %s", attempt + 1, exc.__class__.__name__)
            time.sleep(2)
    # Several workers start at once: serialise schema creation + seeding.
    with engine.connect() as lock_conn:
        lock_conn.execute(text("SELECT pg_advisory_lock(424242)"))
        try:
            Base.metadata.create_all(engine)
            if settings.seed_demo:
                with SessionLocal() as db:
                    seed(db)
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(424242)"))
            lock_conn.commit()
    if settings.jwt_secret == "change-me-in-env":
        log.warning("JWT_SECRET is the default value - set it in .env!")


@app.get("/health", tags=["meta"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
