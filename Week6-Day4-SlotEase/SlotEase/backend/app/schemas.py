from datetime import datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import Appointment, Business, Service

SLUG_RE = r"^[a-z0-9](?:[a-z0-9-]{1,48}[a-z0-9])$"
RESERVED_SLUGS = {"login", "register", "dashboard", "api", "app", "admin", "docs", "assets", "public", "static"}


class RegisterIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=50)
    category: str = Field(default="salon", max_length=40)
    phone: str = Field(default="", max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=20)
    category: str = Field(default="salon", max_length=40)
    address: str = Field(default="", max_length=255)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)


class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_min: int = Field(ge=5, le=600)
    price: Decimal = Field(ge=0, le=1_000_000)
    description: str = Field(default="", max_length=1000)
    is_active: bool = True


class DayHoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    is_open: bool = True
    open_time: time = time(9, 0)
    close_time: time = time(18, 0)

    @field_validator("close_time")
    @classmethod
    def _order(cls, v: time, info):
        o = info.data.get("open_time")
        if info.data.get("is_open", True) and o and v <= o:
            raise ValueError("close_time must be after open_time")
        return v


class WorkingHoursIn(BaseModel):
    days: list[DayHoursIn]


class BookingIn(BaseModel):
    service_id: int
    start_time: datetime
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9 \-]{7,20}$")
    email: EmailStr | None = None
    notes: str = Field(default="", max_length=500)


class StatusIn(BaseModel):
    status: Literal["booked", "completed", "cancelled", "no_show"]


class InsightIn(BaseModel):
    month: str | None = None
    model: str = Field(default="gpt-4o-mini", max_length=60)
    question: str | None = Field(default=None, max_length=500)


# ---------- serializers ----------

def business_out(b: Business) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "slug": b.slug,
        "phone": b.phone,
        "plan": b.plan,
        "category": b.category,
        "address": b.address,
        "timezone": b.timezone,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def service_out(s: Service) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "duration_min": s.duration_min,
        "price": float(s.price),
        "description": s.description,
        "is_active": s.is_active,
    }


def appointment_out(a: Appointment, tz) -> dict:
    return {
        "id": a.id,
        "booking_id": a.booking_ref,
        "start_time": a.start_time.astimezone(tz).isoformat(),
        "end_time": a.end_time.astimezone(tz).isoformat(),
        "status": a.status,
        "source": a.source,
        "notes": a.notes,
        "service": {"id": a.service.id, "name": a.service.name, "price": float(a.service.price),
                    "duration_min": a.service.duration_min},
        "customer": {"id": a.customer.id, "name": a.customer.name, "phone": a.customer.phone,
                     "email": a.customer.email},
    }
