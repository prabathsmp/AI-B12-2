"""The six SlotEase tables. Every tenant-owned table carries business_id."""
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

APPOINTMENT_STATUSES = ("booked", "completed", "cancelled", "no_show")


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    plan: Mapped[str] = mapped_column(String(20), default="starter")
    category: Mapped[str] = mapped_column(String(40), default="salon")
    address: Mapped[str] = mapped_column(String(255), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    business: Mapped[Business] = relationship()


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (CheckConstraint("duration_min > 0", name="ck_service_duration_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    duration_min: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class WorkingHour(Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        UniqueConstraint("business_id", "weekday", name="uq_working_hours_day"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_weekday_range"),
        CheckConstraint("close_time > open_time", name="ck_hours_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = Monday ... 6 = Sunday
    open_time: Mapped[time] = mapped_column(Time)
    close_time: Mapped[time] = mapped_column(Time)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("business_id", "phone", name="uq_customer_phone"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('booked','completed','cancelled','no_show')", name="ck_appointment_status"
        ),
        CheckConstraint("end_time > start_time", name="ck_appointment_order"),
        UniqueConstraint("business_id", "booking_ref", name="uq_appointment_ref"),
        # The core promise: the database itself refuses a second live booking
        # for the same (business, start_time). Cancelled rows free the slot.
        Index(
            "uq_appointment_slot",
            "business_id",
            "start_time",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    booking_ref: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="booked")
    source: Mapped[str] = mapped_column(String(20), default="online")  # online | walk_in
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    service: Mapped[Service] = relationship()
    customer: Mapped[Customer] = relationship()
