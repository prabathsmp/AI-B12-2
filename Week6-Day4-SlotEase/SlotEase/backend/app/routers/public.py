"""Customer-facing endpoints. No auth; tenant resolved by slug."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..booking import compute_slots, create_booking, friendly_when, tz_of
from ..database import get_db
from ..errors import AppError
from ..models import Business, Service, WorkingHour
from ..notify import send_confirmation, wa_link
from ..schemas import BookingIn, service_out

router = APIRouter(prefix="/public", tags=["public"])


def _business(db: Session, slug: str) -> Business:
    b = db.scalar(select(Business).where(Business.slug == slug.lower()))
    if b is None:
        raise AppError(404, "BUSINESS_NOT_FOUND", "We couldn't find that business.")
    return b


@router.get("/{slug}")
def business_profile(slug: str, db: Session = Depends(get_db)):
    b = _business(db, slug)
    hours = list(
        db.scalars(select(WorkingHour).where(WorkingHour.business_id == b.id).order_by(WorkingHour.weekday))
    )
    return {
        "name": b.name,
        "slug": b.slug,
        "phone": b.phone,
        "category": b.category,
        "address": b.address,
        "timezone": b.timezone,
        "today": datetime.now(tz_of(b)).date().isoformat(),
        "open_weekdays": [h.weekday for h in hours],
        "hours": [
            {"weekday": h.weekday, "open_time": h.open_time.strftime("%H:%M"), "close_time": h.close_time.strftime("%H:%M")}
            for h in hours
        ],
    }


@router.get("/{slug}/services")
def public_services(slug: str, db: Session = Depends(get_db)):
    b = _business(db, slug)
    rows = db.scalars(
        select(Service).where(Service.business_id == b.id, Service.is_active.is_(True)).order_by(Service.price)
    )
    return [service_out(s) for s in rows]


@router.get("/{slug}/slots")
def public_slots(
    slug: str,
    service_id: int = Query(...),
    date_: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    b = _business(db, slug)
    today = datetime.now(tz_of(b)).date()
    if date_ < today or date_ > today + timedelta(days=60):
        raise AppError(422, "DATE_OUT_OF_RANGE", "Pick a date within the next 60 days.")
    service = db.scalar(
        select(Service).where(Service.id == service_id, Service.business_id == b.id, Service.is_active.is_(True))
    )
    if service is None:
        raise AppError(404, "SERVICE_NOT_FOUND", "That service is not available.")
    slots = compute_slots(db, b, service, date_)
    return {
        "date": date_.isoformat(),
        "service_id": service.id,
        "closed": not slots and date_.weekday() not in [
            h.weekday for h in db.scalars(select(WorkingHour).where(WorkingHour.business_id == b.id))
        ],
        "free_count": sum(1 for s in slots if s.available),
        "slots": [
            {"start_time": s.start.isoformat(), "end_time": s.end.isoformat(), "label": s.start.strftime("%H:%M"),
             "available": s.available}
            for s in slots
        ],
    }


@router.post("/{slug}/bookings", status_code=201)
def public_book(slug: str, body: BookingIn, db: Session = Depends(get_db)):
    b = _business(db, slug)
    appt = create_booking(db, b.id, body.service_id, body.start_time, body.name, body.phone, body.email, body.notes)
    tz = tz_of(b)
    start = appt.start_time.astimezone(tz)
    message = f"Booking confirmed at {b.name}, {friendly_when(start)}"
    channel = send_confirmation(
        appt.customer.email,
        f"Your booking at {b.name} ({appt.booking_ref})",
        f"Hi {appt.customer.name},\n\n{message} for {appt.service.name}.\nBooking ID: {appt.booking_ref}\n\nSee you soon!",
    )
    return {
        "booking_id": appt.booking_ref,
        "service": appt.service.name,
        "start_time": start.isoformat(),
        "end_time": appt.end_time.astimezone(tz).isoformat(),
        "status": appt.status,
        "message": message,
        "notification": channel,
        "whatsapp_link": wa_link(
            b.phone, f"Hi {b.name}, I just booked {appt.service.name} on {friendly_when(start)} (ID {appt.booking_ref})."
        ),
    }
