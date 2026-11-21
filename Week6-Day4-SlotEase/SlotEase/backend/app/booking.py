"""Slot calculation and race-safe booking.

Double-booking protection is layered:
  1. The business row is locked (SELECT ... FOR UPDATE) for the duration of the
     booking transaction, so concurrent bookings for one tenant are serialised and
     the overlap check below sees every committed booking.
  2. Overlap check: a new appointment may not intersect any live appointment.
  3. The database's partial unique index uq_appointment_slot on
     (business_id, start_time) WHERE status <> 'cancelled' refuses a duplicate
     even if application logic were bypassed. IntegrityError -> 409 SLOT_TAKEN.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .errors import AppError
from .models import Appointment, Business, Customer, Service, WorkingHour

SLOT_TAKEN = AppError(409, "SLOT_TAKEN", "This slot was just booked. Please pick another time.")


def tz_of(business: Business) -> ZoneInfo:
    try:
        return ZoneInfo(business.timezone or settings.default_timezone)
    except Exception:  # noqa: BLE001 - bad tz string falls back to default
        return ZoneInfo(settings.default_timezone)


def day_bounds(business: Business, day: date) -> tuple[datetime, datetime]:
    tz = tz_of(business)
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def live_appointments(db: Session, business_id: int, start: datetime, end: datetime) -> list[Appointment]:
    """Non-cancelled appointments that intersect [start, end)."""
    return list(
        db.scalars(
            select(Appointment).where(
                Appointment.business_id == business_id,
                Appointment.status != "cancelled",
                Appointment.start_time < end,
                Appointment.end_time > start,
            )
        )
    )


@dataclass
class Slot:
    start: datetime
    end: datetime
    available: bool


def compute_slots(db: Session, business: Business, service: Service, day: date) -> list[Slot]:
    """Working hours for the weekday, stepped every SLOT_STEP minutes, minus booked time."""
    tz = tz_of(business)
    hours = db.scalar(
        select(WorkingHour).where(WorkingHour.business_id == business.id, WorkingHour.weekday == day.weekday())
    )
    if hours is None:
        return []

    open_at = datetime.combine(day, hours.open_time, tzinfo=tz)
    close_at = datetime.combine(day, hours.close_time, tzinfo=tz)
    duration = timedelta(minutes=service.duration_min)
    step = timedelta(minutes=settings.slot_step_minutes)
    now = datetime.now(timezone.utc)
    booked = live_appointments(db, business.id, open_at, close_at)

    slots: list[Slot] = []
    cursor = open_at
    while cursor + duration <= close_at:
        end = cursor + duration
        clash = any(a.start_time < end and a.end_time > cursor for a in booked)
        if cursor > now:  # never offer past times
            slots.append(Slot(cursor, end, not clash))
        cursor += step
    return slots


def _validate_slot(db: Session, business: Business, service: Service, start_local: datetime) -> datetime:
    tz = tz_of(business)
    hours = db.scalar(
        select(WorkingHour).where(
            WorkingHour.business_id == business.id, WorkingHour.weekday == start_local.weekday()
        )
    )
    if hours is None:
        raise AppError(422, "CLOSED", f"{business.name} is closed on that day.")
    open_at = datetime.combine(start_local.date(), hours.open_time, tzinfo=tz)
    close_at = datetime.combine(start_local.date(), hours.close_time, tzinfo=tz)
    end_local = start_local + timedelta(minutes=service.duration_min)
    if start_local < open_at or end_local > close_at:
        raise AppError(422, "OUTSIDE_HOURS", "That time is outside working hours.")
    offset_min = int((start_local - open_at).total_seconds() // 60)
    if offset_min % settings.slot_step_minutes != 0 or start_local.second or start_local.microsecond:
        raise AppError(422, "INVALID_SLOT", "Please choose one of the offered slots.")
    if start_local <= datetime.now(timezone.utc):
        raise AppError(422, "PAST_SLOT", "That time has already passed.")
    return end_local


def _next_ref(db: Session, business: Business, start_local: datetime) -> str:
    day_start, day_end = day_bounds(business, start_local.date())
    count = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.business_id == business.id,
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )
    )
    return f"APT-{start_local:%Y%m%d}-{(count or 0) + 1:04d}"


def create_booking(
    db: Session,
    business_id: int,
    service_id: int,
    start_time: datetime,
    name: str,
    phone: str,
    email: str | None = None,
    notes: str = "",
    source: str = "online",
) -> Appointment:
    # Lock the tenant row: serialises concurrent bookings for this business.
    business = db.scalar(select(Business).where(Business.id == business_id).with_for_update())
    if business is None:
        raise AppError(404, "NOT_FOUND", "Business not found.")
    service = db.scalar(
        select(Service).where(
            Service.id == service_id, Service.business_id == business.id, Service.is_active.is_(True)
        )
    )
    if service is None:
        raise AppError(404, "SERVICE_NOT_FOUND", "That service is not available.")

    tz = tz_of(business)
    start_local = (start_time if start_time.tzinfo else start_time.replace(tzinfo=tz)).astimezone(tz)
    end_local = _validate_slot(db, business, service, start_local)

    if live_appointments(db, business.id, start_local, end_local):
        db.rollback()
        raise SLOT_TAKEN

    phone_norm = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    customer = db.scalar(
        select(Customer).where(Customer.business_id == business.id, Customer.phone == phone_norm)
    )
    if customer is None:
        customer = Customer(business_id=business.id, name=name.strip(), phone=phone_norm, email=email or None)
        db.add(customer)
        db.flush()
    else:
        customer.name = name.strip() or customer.name
        if email:
            customer.email = email

    appt = Appointment(
        business_id=business.id,
        service_id=service.id,
        customer_id=customer.id,
        booking_ref=_next_ref(db, business, start_local),
        start_time=start_local,
        end_time=end_local,
        status="booked",
        source=source,
        notes=notes or "",
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        # The database refused it (uq_appointment_slot) - someone won the race.
        db.rollback()
        raise SLOT_TAKEN
    db.refresh(appt)
    return appt


def friendly_when(dt: datetime) -> str:
    """'Sat 10 Oct, 5:30 PM' (portable - no %-d)."""
    hour12 = dt.hour % 12 or 12
    return f"{dt:%a} {dt.day} {dt:%b}, {hour12}:{dt:%M} {'AM' if dt.hour < 12 else 'PM'}"
