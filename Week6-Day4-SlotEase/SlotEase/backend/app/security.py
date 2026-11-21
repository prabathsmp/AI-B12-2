from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .errors import AppError
from .models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "bid": user.business_id,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise AppError(401, "UNAUTHORIZED", "Please log in.")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Your session has expired. Please log in again.")
    except jwt.PyJWTError:
        raise AppError(401, "UNAUTHORIZED", "Invalid token.")
    user = db.get(User, int(payload["sub"]))
    if user is None or user.business_id != payload.get("bid"):
        raise AppError(401, "UNAUTHORIZED", "Invalid token.")
    return user
