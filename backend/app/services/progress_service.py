"""ProgressService — manages weight/body-fat/sleep logs and body measurements."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.body_measurement import BodyMeasurement
from app.models.progress_log import ProgressLog
from app.repositories import progress_repository


class ProgressService:
    def _today(self) -> str:
        return datetime.now(UTC).date().isoformat()

    # ── Progress Logs ──────────────────────────────────────────────────────

    def log_progress(
        self,
        db: Session,
        user_id: str,
        log_date: str | None,
        weight_kg: float | None,
        body_fat_pct: float | None,
        sleep_hours: float | None,
        notes: str | None,
    ) -> ProgressLog:
        date_str = log_date or self._today()
        return progress_repository.upsert(
            db,
            user_id=user_id,
            log_date=date_str,
            fields={
                "weight_kg": weight_kg,
                "body_fat_pct": body_fat_pct,
                "sleep_hours": sleep_hours,
                "notes": notes,
            },
        )

    def get_logs(self, db: Session, user_id: str, limit: int = 90) -> list[ProgressLog]:
        return progress_repository.list_by_user(db, user_id, limit=limit)

    def get_summary(self, db: Session, user_id: str) -> dict:
        logs = progress_repository.list_by_user(db, user_id, limit=90)
        weight_logs = [entry for entry in logs if entry.weight_kg is not None]
        recent = logs[0] if logs else None

        # Weight change vs. 30-day-ago entry
        weight_change_30d: float | None = None
        if len(weight_logs) >= 2:
            oldest = weight_logs[-1]
            newest = weight_logs[0]
            weight_change_30d = round((newest.weight_kg or 0) - (oldest.weight_kg or 0), 1)

        return {
            "current_weight_kg": recent.weight_kg if recent else None,
            "current_body_fat_pct": recent.body_fat_pct if recent else None,
            "last_sleep_hours": recent.sleep_hours if recent else None,
            "weight_change_30d_kg": weight_change_30d,
            "total_logs": len(logs),
            "weight_entries": len(weight_logs),
        }

    # ── Body Measurements ──────────────────────────────────────────────────

    def log_measurement(
        self,
        db: Session,
        user_id: str,
        log_date: str | None,
        **fields: float | None,
    ) -> BodyMeasurement:
        date_str = log_date or self._today()
        return progress_repository.upsert_measurement(
            db, user_id=user_id, log_date=date_str, fields=fields
        )

    def get_measurements(self, db: Session, user_id: str, limit: int = 30) -> list[BodyMeasurement]:
        return progress_repository.list_measurements_by_user(db, user_id, limit=limit)
