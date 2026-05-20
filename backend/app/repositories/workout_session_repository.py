"""Data access for `WorkoutSession`."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import WorkoutSessionStatus
from app.models.workout_session import WorkoutSession


def get_by_id(db: Session, session_id: str) -> WorkoutSession | None:
    """Eagerly loads `exercise_completions` so the caller never triggers a
    lazy load when serializing the response."""
    query = (
        select(WorkoutSession)
        .where(WorkoutSession.id == session_id)
        .options(joinedload(WorkoutSession.exercise_completions))
    )
    return db.execute(query).unique().scalars().first()


def get_active_or_paused_for_user(db: Session, user_id: str) -> WorkoutSession | None:
    """The session a user is currently "in" — `active` or `paused`, the two
    statuses that count as "already has a session open" for the
    one-session-at-a-time business rule. `completed` sessions don't block a
    new one from starting."""
    query = (
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status.in_([WorkoutSessionStatus.active, WorkoutSessionStatus.paused]),
        )
        .options(joinedload(WorkoutSession.exercise_completions))
        .limit(1)
    )
    return db.execute(query).unique().scalars().first()


def list_history_for_user(db: Session, user_id: str) -> list[WorkoutSession]:
    """Every completed session for a user, most recent first. History is
    never deleted, so this list only grows — see the model docstring for why
    `workout_plan_id` is denormalized here rather than joined."""
    query = (
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == WorkoutSessionStatus.completed,
        )
        .options(joinedload(WorkoutSession.exercise_completions))
        .order_by(WorkoutSession.completed_at.desc())
    )
    return list(db.execute(query).unique().scalars().all())


def create(db: Session, *, user_id: str, fields: dict) -> WorkoutSession:
    now = datetime.now(UTC)
    session = WorkoutSession(
        user_id=user_id,
        started_at=now,
        last_resumed_at=now,
        accumulated_active_seconds=0,
        **fields,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update(db: Session, *, session: WorkoutSession, fields: dict) -> WorkoutSession:
    for key, value in fields.items():
        setattr(session, key, value)
    db.commit()
    db.refresh(session)
    return session
