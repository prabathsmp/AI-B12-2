"""Optional AI features. The OpenAI key is supplied by the owner in the UI and sent
per request in the X-OpenAI-Key header. It is never stored or logged server-side.
Without a key the app works fully; rule-based insights are always in /stats."""
import json

import httpx
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import AppError
from ..models import User
from ..schemas import InsightIn, ServiceIn
from ..security import current_user
from .owner import compute_stats

router = APIRouter(prefix="/ai", tags=["ai (optional)"])
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def _chat(key: str | None, model: str, system: str, user_msg: str, max_tokens: int = 500) -> str:
    if not key or not key.strip():
        raise AppError(400, "NO_API_KEY", "Add your OpenAI API key in Settings to use AI features.")
    try:
        r = httpx.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key.strip()}"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
                "max_tokens": max_tokens,
                "temperature": 0.4,
            },
            timeout=45,
        )
    except httpx.HTTPError:
        raise AppError(502, "AI_UNREACHABLE", "Could not reach OpenAI. Check your network and try again.")
    if r.status_code == 401:
        raise AppError(400, "INVALID_API_KEY", "OpenAI rejected the API key.")
    if r.status_code >= 400:
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except ValueError:
            detail = r.text
        raise AppError(502, "AI_ERROR", f"OpenAI error: {detail[:200]}")
    return r.json()["choices"][0]["message"]["content"].strip()


@router.post("/insights")
def ai_insights(
    body: InsightIn,
    x_openai_key: str | None = Header(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stats = compute_stats(db, user.business, body.month)
    compact = {k: v for k, v in stats.items() if k != "daily"}
    system = (
        "You are a friendly business coach for small Indian clinics and salons using an appointment app. "
        "Give 4-6 short, specific, actionable bullet points in plain language based only on the data. "
        "Currency is Indian Rupees (Rs). No preamble."
    )
    question = body.question or "How can I get more bookings and fewer no-shows next month?"
    text = _chat(
        x_openai_key, body.model, system,
        f"Business: {user.business.name} ({user.business.category}).\nStats JSON: {json.dumps(compact)}\n"
        f"Question: {question}",
    )
    return {"model": body.model, "answer": text}


@router.post("/service-description")
def ai_service_description(
    body: ServiceIn,
    x_openai_key: str | None = Header(default=None),
    model: str = "gpt-4o-mini",
    user: User = Depends(current_user),
):
    text = _chat(
        x_openai_key, model,
        "Write a warm, 1-2 sentence description (max 220 characters) for a service on a booking page. No quotes.",
        f"Business type: {user.business.category}. Service: {body.name}, {body.duration_min} minutes, Rs {body.price}.",
        max_tokens=120,
    )
    return {"description": text[:300]}
