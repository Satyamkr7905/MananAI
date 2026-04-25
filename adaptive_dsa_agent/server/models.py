# ORM models — users, OTP rows, persisted tutor state.

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # bcrypt hash. NULL for google-only or legacy OTP-only accounts.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # true once email is proven (OTP confirmed or Google verified).
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    learning: Mapped["UserLearningState"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    behavior_events: Mapped[list["UserBehaviorEvent"]] = relationship(
        "UserBehaviorEvent",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserLearningState(Base):
    __tablename__ = "user_learning_state"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tutor_state_json: Mapped[str] = mapped_column(Text, default="{}")
    solved_first_try_json: Mapped[str] = mapped_column(Text, default="[]")
    current_qid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts_on_current: Mapped[int] = mapped_column(default=0)

    user: Mapped["User"] = relationship(back_populates="learning")


class UserBehaviorEvent(Base):
    # append-only log for learning analytics and improvement history.

    __tablename__ = "user_behavior_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="behavior_events")


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
