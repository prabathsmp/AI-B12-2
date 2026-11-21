"""Runtime configuration, read from environment variables (see .env.example)."""
import os


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://slotease:slotease@localhost:5432/slotease"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-env")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",") if o.strip()
    ]
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    slot_step_minutes: int = int(os.getenv("SLOT_STEP_MINUTES", "15"))
    seed_demo: bool = _bool("SEED_DEMO", True)

    # Optional SMTP for e-mail confirmations. When SMTP_HOST is empty the
    # confirmation is only logged and a WhatsApp click-to-chat link is returned.
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "SlotEase <no-reply@slotease.local>")


settings = Settings()
