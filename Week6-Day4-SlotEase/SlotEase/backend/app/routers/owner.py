"""Owner dashboard endpoints. Every query is scoped by the JWT's business_id."""
import calendar
from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..booking import create_booking, day_bounds, tz_of
from ..database import get_db
from ..errors import AppError
from ..models import Appointment, Business, Customer, Service, User, WorkingHour
from ..notify import wa_link
from ..schemas import (
    BookingIn,
    BusinessIn,
    ServiceIn,
    StatusIn,
    WorkingHoursIn,
    appointment_out,
    business_out,
    service_out,
)
from ..security import current_user

router = APIRouter(tags=["owner"])
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _biz(user: User) -> Business:
    return user.business


# ---------------- business profile ----------------

@router.get("/business")
def get_business(user: User = Depends(current_user)):
    return business_out(_biz(user))


@router.put("/business")
def update_business(body: BusinessIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        ZoneInfo(body.timezone)
    except Exception:  # noqa: BLE001
        raise AppError(422, "INVALID_TIMEZONE", "Unknown timezone.")
    b = db.get(Business, user.business_id)
    for k, v in body.model_dump().items():
        setattr(b, k, v)
    db.commit()
    return business_out(b)


# ---------------- appointments ----------------

def _appt_query(business_id: int):
    return (
        select(Appointment)
        .options(joinedload(Appointment.service), joinedload(Appointment.customer))
        .where(Appointment.business_id == business_id)
    )


@router.get("/appointments")
def list_appointments(
    date_: date | None = Query(None, alias="date"),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    b = _biz(user)
    tz = tz_of(b)
    if from_ and to:
        if (to - from_).days > 62:
            raise AppError(422, "RANGE_TOO_LARGE", "Pick a range of at most 62 days.")
        start, _ = day_bounds(b, from_)
        _, end = day_bounds(b, to)
    else:
        start, end = day_bounds(b, date_ or datetime.now(tz).date())
    rows = db.scalars(
        _appt_query(b.id).where(Appointment.start_time >= start, Appointment.start_time < end).order_by(Appointment.start_time)
    ).unique()
    out = []
    for a in rows:
        item = appointment_out(a, tz)
        item["whatsapp_link"] = wa_link(
            a.customer.phone,
            f"Hi {a.customer.name}, this is {b.name} about your {a.service.name} booking ({a.booking_ref}).",
        )
        out.append(item)
    return out


@router.post("/appointments", status_code=201)
def create_walk_in(body: BookingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    appt = create_booking(
        db, user.business_id, body.service_id, body.start_time, body.name, body.phone, body.email, body.notes,
        source="walk_in",
    )
    appt = db.scalars(_appt_query(user.business_id).where(Appointment.id == appt.id)).unique().one()
    return appointment_out(appt, tz_of(_biz(user)))


@router.patch("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int, body: StatusIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    appt = db.scalars(_appt_query(user.business_id).where(Appointment.id == appointment_id)).unique().one_or_none()
    if appt is None:  # also what another tenant sees - no information leak
        raise AppError(404, "NOT_FOUND", "Appointment not found.")
    appt.status = body.status
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "SLOT_TAKEN", "That slot has been re-booked, so this appointment can't be restored.")
    return appointment_out(appt, tz_of(_biz(user)))


# ---------------- customers ----------------

@router.get("/customers")
def list_customers(user: User = Depends(current_user), db: Session = Depends(get_db)):
    visits = (
        select(
            Appointment.customer_id,
            func.count(Appointment.id).label("visits"),
            func.sum(case((Appointment.status == "no_show", 1), else_=0)).label("no_shows"),
            func.max(Appointment.start_time).label("last_visit"),
        )
        .where(Appointment.business_id == user.business_id)
        .group_by(Appointment.customer_id)
        .subquery()
    )
    rows = db.execute(
        select(Customer, visits.c.visits, visits.c.no_shows, visits.c.last_visit)
        .outerjoin(visits, visits.c.customer_id == Customer.id)
        .where(Customer.business_id == user.business_id)
        .order_by(visits.c.last_visit.desc().nullslast())
    ).all()
    tz = tz_of(_biz(user))
    return [
        {"id": c.id, "name": c.name, "phone": c.phone, "email": c.email, "visits": v or 0, "no_shows": int(n or 0),
         "last_visit": lv.astimezone(tz).isoformat() if lv else None}
        for c, v, n, lv in rows
    ]


# ---------------- services ----------------

def _service(db: Session, user: User, service_id: int) -> Service:
    s = db.scalar(select(Service).where(Service.id == service_id, Service.business_id == user.business_id))
    if s is None:
        raise AppError(404, "NOT_FOUND", "Service not found.")
    return s


@router.get("/services")
def list_services(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Service).where(Service.business_id == user.business_id).order_by(Service.name))
    return [service_out(s) for s in rows]


@router.post("/services", status_code=201)
def create_service(body: ServiceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = Service(business_id=user.business_id, **body.model_dump())
    db.add(s)
    db.commit()
    return service_out(s)


@router.get("/services/{service_id}")
def get_service(service_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return service_out(_service(db, user, service_id))


@router.put("/services/{service_id}")
def update_service(service_id: int, body: ServiceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _service(db, user, service_id)
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return service_out(s)


@router.delete("/services/{service_id}")
def delete_service(service_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _service(db, user, service_id)
    used = db.scalar(select(func.count(Appointment.id)).where(Appointment.service_id == s.id))
    if used:
        # Keep history intact - archive instead of deleting.
        s.is_active = False
        db.commit()
        return {"deleted": False, "archived": True, "message": "Service has bookings, so it was archived instead."}
    db.delete(s)
    db.commit()
    return {"deleted": True, "archived": False, "message": "Service deleted."}


# ---------------- working hours ----------------

def _hours_out(db: Session, business_id: int) -> list[dict]:
    rows = {h.weekday: h for h in db.scalars(select(WorkingHour).where(WorkingHour.business_id == business_id))}
    out = []
    for wd in range(7):
        h = rows.get(wd)
        out.append({
            "weekday": wd,
            "name": WEEKDAYS[wd],
            "is_open": h is not None,
            "open_time": h.open_time.strftime("%H:%M") if h else "09:00",
            "close_time": h.close_time.strftime("%H:%M") if h else "18:00",
        })
    return out


@router.get("/working-hours")
def get_hours(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _hours_out(db, user.business_id)


@router.put("/working-hours")
def put_hours(body: WorkingHoursIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if len({d.weekday for d in body.days}) != len(body.days):
        raise AppError(422, "DUPLICATE_DAY", "Each weekday may appear only once.")
    db.execute(delete(WorkingHour).where(WorkingHour.business_id == user.business_id))
    for d in body.days:
        if d.is_open:
            db.add(WorkingHour(business_id=user.business_id, weekday=d.weekday, open_time=d.open_time,
                               close_time=d.close_time))
    db.commit()
    return _hours_out(db, user.business_id)


# ---------------- stats ----------------

def compute_stats(db: Session, b: Business, month: str | None) -> dict:
    tz = tz_of(b)
    today = datetime.now(tz).date()
    try:
        year, mon = (int(x) for x in (month or f"{today:%Y-%m}").split("-"))
        first = date(year, mon, 1)
    except (ValueError, TypeError):
        raise AppError(422, "INVALID_MONTH", "Use month=YYYY-MM.")
    days_in = calendar.monthrange(year, mon)[1]
    start, _ = day_bounds(b, first)
    _, end = day_bounds(b, date(year, mon, days_in))

    appts = list(
        db.scalars(
            _appt_query(b.id).where(Appointment.start_time >= start, Appointment.start_time < end)
        ).unique()
    )
    status = Counter(a.status for a in appts)
    live = [a for a in appts if a.status != "cancelled"]
    resolved = status["completed"] + status["no_show"]
    no_show_rate = round(100 * status["no_show"] / resolved, 1) if resolved else 0.0
    revenue_done = sum(float(a.service.price) for a in appts if a.status == "completed")
    revenue_pipe = sum(float(a.service.price) for a in appts if a.status == "booked")

    by_weekday = Counter(a.start_time.astimezone(tz).weekday() for a in live)
    by_day = Counter(a.start_time.astimezone(tz).day for a in live)
    by_hour = Counter(a.start_time.astimezone(tz).hour for a in live)
    by_service = Counter(a.service.name for a in live)
    rev_service = Counter()
    for a in appts:
        if a.status in ("completed", "booked"):
            rev_service[a.service.name] += float(a.service.price)

    busiest = WEEKDAYS[by_weekday.most_common(1)[0][0]] if by_weekday else None
    peak_hour = by_hour.most_common(1)[0][0] if by_hour else None

    customer_ids = {a.customer_id for a in live}
    earlier = set()
    if customer_ids:
        earlier = set(db.scalars(
            select(Appointment.customer_id).where(
                Appointment.business_id == b.id, Appointment.start_time < start,
                Appointment.customer_id.in_(customer_ids),
            ).distinct()
        ))

    insights = []
    if live:
        insights.append(f"{len(live)} bookings this month; {busiest} is your busiest day.")
    if peak_hour is not None:
        insights.append(f"Peak time is around {peak_hour % 12 or 12} {'AM' if peak_hour < 12 else 'PM'} - keep full staff then.")
    if no_show_rate >= 10:
        insights.append(f"No-show rate is {no_show_rate}%. Send WhatsApp reminders the day before.")
    elif resolved:
        insights.append(f"No-show rate is a healthy {no_show_rate}%.")
    if by_service:
        top, cnt = by_service.most_common(1)[0]
        insights.append(f"'{top}' is the most booked service ({cnt} bookings).")
    if customer_ids:
        insights.append(f"{len(earlier)} of {len(customer_ids)} customers are repeat visitors.")

    return {
        "month": f"{year:04d}-{mon:02d}",
        "total_bookings": len(live),
        "completed": status["completed"],
        "no_shows": status["no_show"],
        "cancelled": status["cancelled"],
        "upcoming": status["booked"],
        "no_show_rate": no_show_rate,
        "revenue_completed": revenue_done,
        "revenue_estimate": revenue_done + revenue_pipe,
        "busiest_day": busiest,
        "peak_hour": peak_hour,
        "unique_customers": len(customer_ids),
        "repeat_customers": len(earlier),
        "daily": [{"day": d, "bookings": by_day.get(d, 0)} for d in range(1, days_in + 1)],
        "weekday": [{"weekday": WEEKDAYS[i][:3], "bookings": by_weekday.get(i, 0)} for i in range(7)],
        "services": [{"name": n, "bookings": c, "revenue": rev_service.get(n, 0)} for n, c in by_service.most_common(8)],
        "insights": insights,
    }


@router.get("/stats")
def stats(month: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return compute_stats(db, _biz(user), month)
