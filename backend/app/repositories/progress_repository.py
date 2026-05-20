"""Data access for ProgressLog and BodyMeasurement."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.body_measurement import BodyMeasurement
from app.models.progress_log import ProgressLog

# ── ProgressLog ────────────────────────────────────────────────────────────


def get_by_user_and_date(db: Session, user_id: str, log_date: str) -> ProgressLog | None:
    return (
        db.execute(
            select(ProgressLog).where(
                ProgressLog.user_id == user_id,
                ProgressLog.log_date == log_date,
            )
        )
        .scalars()
        .first()
    )


def list_by_user(db: Session, user_id: str, limit: int = 90) -> list[ProgressLog]:
    return list(
        db.execute(
            select(ProgressLog)
            .where(ProgressLog.user_id == user_id)
            .order_by(ProgressLog.log_date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def upsert(db: Session, user_id: str, log_date: str, fields: dict) -> ProgressLog:
    existing = get_by_user_and_date(db, user_id, log_date)
    if existing:
        for k, v in fields.items():
            if v is not None:
                setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    log = ProgressLog(user_id=user_id, log_date=log_date, **fields)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def delete(db: Session, log: ProgressLog) -> None:
    db.delete(log)
    db.commit()


# ── BodyMeasurement ────────────────────────────────────────────────────────


def get_measurement_by_user_and_date(
    db: Session, user_id: str, log_date: str
) -> BodyMeasurement | None:
    return (
        db.execute(
            select(BodyMeasurement).where(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.log_date == log_date,
            )
        )
        .scalars()
        .first()
    )


def list_measurements_by_user(db: Session, user_id: str, limit: int = 30) -> list[BodyMeasurement]:
    return list(
        db.execute(
            select(BodyMeasurement)
            .where(BodyMeasurement.user_id == user_id)
            .order_by(BodyMeasurement.log_date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def upsert_measurement(db: Session, user_id: str, log_date: str, fields: dict) -> BodyMeasurement:
    existing = get_measurement_by_user_and_date(db, user_id, log_date)
    if existing:
        for k, v in fields.items():
            if v is not None:
                setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    m = BodyMeasurement(user_id=user_id, log_date=log_date, **fields)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
