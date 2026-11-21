import re
from datetime import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..errors import AppError
from ..models import Business, User, WorkingHour
from ..schemas import RESERVED_SLUGS, SLUG_RE, LoginIn, RegisterIn, business_out
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:50] or "business"


def _auth_payload(user: User, business: Business) -> dict:
    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "role": user.role},
        "business": business_out(business),
    }


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise AppError(409, "EMAIL_TAKEN", "An account with this e-mail already exists.")

    slug = slugify(body.slug or body.business_name)
    if not re.match(SLUG_RE, slug) or slug in RESERVED_SLUGS:
        raise AppError(422, "INVALID_SLUG", "Choose a booking link of 3-50 letters, numbers or dashes.")
    if body.slug and db.scalar(select(Business).where(Business.slug == slug)):
        raise AppError(409, "SLUG_TAKEN", "That booking link is already taken.")
    base, n = slug, 2
    while db.scalar(select(Business).where(Business.slug == slug)):
        slug, n = f"{base}-{n}", n + 1

    business = Business(name=body.business_name.strip(), slug=slug, phone=body.phone, category=body.category,
                        timezone=settings.default_timezone)
    db.add(business)
    db.flush()
    user = User(business_id=business.id, email=email, password_hash=hash_password(body.password), role="owner")
    db.add(user)
    # Sensible default: Mon-Sat 09:00-18:00, Sunday closed.
    for wd in range(6):
        db.add(WorkingHour(business_id=business.id, weekday=wd, open_time=time(9), close_time=time(18)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "CONFLICT", "That e-mail or booking link is already in use.")
    return _auth_payload(user, business)


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Wrong e-mail or password.")
    return _auth_payload(user, user.business)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user": {"id": user.id, "email": user.email, "role": user.role}, "business": business_out(user.business)}
