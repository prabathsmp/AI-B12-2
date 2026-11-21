"""Demo tenants so the app is explorable on first run (SEED_DEMO=true).

glow-salon   owner: demo@slotease.app   / demo1234
care-physio  owner: physio@slotease.app / demo1234   (second tenant for isolation tests)
"""
import logging
import random
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .booking import tz_of
from .models import Appointment, Business, Customer, Service, User, WorkingHour
from .security import hash_password

log = logging.getLogger("slotease.seed")

FIRST = ["Priya", "Arun", "Karthik", "Divya", "Meena", "Rahul", "Sneha", "Vijay", "Anjali", "Suresh",
         "Lakshmi", "Ravi", "Pooja", "Manoj", "Keerthi", "Ganesh", "Nisha", "Harish", "Deepa", "Ajay"]
LAST = "RKSMPVNTAG"

TENANTS = [
    {
        "name": "Glow Salon", "slug": "glow-salon", "phone": "9876543210", "category": "salon",
        "address": "12 Anna Nagar 2nd Ave, Chennai", "email": "demo@slotease.app",
        "hours": {wd: (time(10), time(20)) for wd in range(6)} | {6: (time(10), time(14))},
        "services": [
            ("Haircut", 30, 300, "Precision cut and style by our senior stylists."),
            ("Beard Trim", 15, 150, "Clean shape-up with hot towel finish."),
            ("Haircut + Beard", 45, 400, "Our most-loved combo for a sharp, fresh look."),
            ("Hair Spa", 60, 900, "Deep-conditioning treatment for smooth, healthy hair."),
            ("Facial - Classic", 45, 700, "Cleansing, exfoliation and massage for glowing skin."),
            ("Hair Colour", 90, 1500, "Global colour with ammonia-free products."),
        ],
    },
    {
        "name": "CarePlus Physio", "slug": "care-physio", "phone": "9123456780", "category": "physiotherapy",
        "address": "45 Indiranagar 100ft Rd, Bengaluru", "email": "physio@slotease.app",
        "hours": {wd: (time(8), time(19)) for wd in range(5)} | {5: (time(9), time(13))},
        "services": [
            ("Initial Assessment", 45, 800, "Full posture and mobility assessment with a plan."),
            ("Physio Session", 30, 600, "Targeted therapy session with exercises."),
            ("Sports Massage", 60, 1200, "Deep tissue massage for recovery."),
        ],
    },
]


def seed(db: Session) -> None:
    rnd = random.Random(42)
    for t in TENANTS:
        if db.scalar(select(Business).where(Business.slug == t["slug"])):
            continue
        b = Business(name=t["name"], slug=t["slug"], phone=t["phone"], category=t["category"],
                     address=t["address"], plan="starter")
        db.add(b)
        db.flush()
        db.add(User(business_id=b.id, email=t["email"], password_hash=hash_password("demo1234"), role="owner"))
        for wd, (o, c) in t["hours"].items():
            db.add(WorkingHour(business_id=b.id, weekday=wd, open_time=o, close_time=c))
        services = [Service(business_id=b.id, name=n, duration_min=d, price=p, description=desc)
                    for n, d, p, desc in t["services"]]
        db.add_all(services)
        customers = []
        for i in range(28):
            customers.append(Customer(business_id=b.id, name=f"{rnd.choice(FIRST)} {rnd.choice(LAST)}",
                                      phone=f"98{rnd.randint(10_000_000, 99_999_999)}"))
        db.add_all(customers)
        db.flush()

        tz = tz_of(b)
        now = datetime.now(tz)
        today = now.date()
        counters: dict = {}
        for offset in range(-35, 8):
            day = today + timedelta(days=offset)
            if day.weekday() not in t["hours"]:
                continue
            o, c = t["hours"][day.weekday()]
            cursor = datetime.combine(day, o, tzinfo=tz)
            close = datetime.combine(day, c, tzinfo=tz)
            density = 0.55 if day.weekday() == 5 else 0.35
            while cursor < close:
                svc = rnd.choice(services)
                end = cursor + timedelta(minutes=svc.duration_min)
                if end > close:
                    break
                if rnd.random() < density:
                    if end <= now:
                        status = rnd.choices(["completed", "no_show", "cancelled"], [86, 8, 6])[0]
                    else:
                        status = rnd.choices(["booked", "cancelled"], [94, 6])[0]
                    counters[day] = counters.get(day, 0) + 1
                    db.add(Appointment(
                        business_id=b.id, service_id=svc.id, customer_id=rnd.choice(customers).id,
                        booking_ref=f"APT-{day:%Y%m%d}-{counters[day]:04d}", start_time=cursor, end_time=end,
                        status=status, source=rnd.choice(["online", "online", "online", "walk_in"]),
                    ))
                    cursor = end
                else:
                    cursor += timedelta(minutes=15)
        db.commit()
        log.info("Seeded demo tenant %s", t["slug"])
