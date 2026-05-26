"""WorkoutStatsService — aggregate statistics computed from completed sessions.

Pure computation over already-persisted data — no writes, no side effects.
Kept as a class for consistency with the other services even though it has no
instance state; it could be module-level functions equally well, but the class
pattern keeps imports and dependency injection uniform.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import WorkoutSessionStatus
from app.models.exercise_completion import ExerciseCompletion
from app.models.workout_session import WorkoutSession
from app.repositories import workout_session_repository


class WorkoutStatsService:
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_summary(self, db: Session, user_id: str) -> dict:
        """Dashboard-level summary: totals, streak, recent activity."""
        sessions = workout_session_repository.list_history_for_user(db, user_id)

        total_sessions = len(sessions)
        total_minutes = sum(s.total_duration_minutes or 0 for s in sessions)
        total_calories = sum(s.calories_burned_estimate or 0 for s in sessions)
        total_exercises_completed = self._count_completed_exercises(db, user_id)

        current_streak, longest_streak = self._compute_streaks(sessions)

        # Sessions in the last 7 and 30 days
        now = datetime.now(UTC)
        last_7 = [
            s
            for s in sessions
            if s.completed_at and (now - self._to_aware(s.completed_at)).days < 7
        ]
        last_30 = [
            s
            for s in sessions
            if s.completed_at and (now - self._to_aware(s.completed_at)).days < 30
        ]

        return {
            "total_sessions": total_sessions,
            "total_minutes": total_minutes,
            "total_calories_burned": round(total_calories, 1),
            "total_exercises_completed": total_exercises_completed,
            "current_streak_days": current_streak,
            "longest_streak_days": longest_streak,
            "sessions_last_7_days": len(last_7),
            "sessions_last_30_days": len(last_30),
            "avg_session_minutes": (
                round(total_minutes / total_sessions, 1) if total_sessions else 0
            ),
            "avg_calories_per_session": (
                round(total_calories / total_sessions, 1) if total_sessions else 0
            ),
        }

    def get_weekly_volume(self, db: Session, user_id: str, weeks: int = 8) -> list[dict]:
        """Weekly session counts and total minutes for the last `weeks` weeks.
        Returns one entry per week, oldest first — ready to feed a chart."""
        sessions = workout_session_repository.list_history_for_user(db, user_id)
        now = datetime.now(UTC)
        result = []
        for w in range(weeks - 1, -1, -1):
            week_start = now - timedelta(days=now.weekday() + 7 * w)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            week_sessions = [
                s
                for s in sessions
                if s.completed_at and week_start <= self._to_aware(s.completed_at) < week_end
            ]
            result.append(
                {
                    "week_start": week_start.date().isoformat(),
                    "sessions": len(week_sessions),
                    "minutes": sum(s.total_duration_minutes or 0 for s in week_sessions),
                    "calories": round(
                        sum(s.calories_burned_estimate or 0 for s in week_sessions), 1
                    ),
                }
            )
        return result

    def get_personal_records(self, db: Session, user_id: str) -> list[dict]:
        """Best session by duration, most exercises completed in one session,
        most calories burned in one session — the three PRs the UI displays."""
        sessions = workout_session_repository.list_history_for_user(db, user_id)
        if not sessions:
            return []

        best_duration = max(sessions, key=lambda s: s.total_duration_minutes or 0)
        most_calories = max(sessions, key=lambda s: s.calories_burned_estimate or 0)
        most_completed = max(
            sessions,
            key=lambda s: sum(1 for c in s.exercise_completions if c.completed),
        )

        records = [
            {
                "type": "longest_session",
                "label": "Longest session",
                "value": best_duration.total_duration_minutes or 0,
                "unit": "min",
                "session_id": best_duration.id,
                "achieved_at": (
                    best_duration.completed_at.isoformat() if best_duration.completed_at else None
                ),
            },
            {
                "type": "most_calories",
                "label": "Most calories burned",
                "value": round(most_calories.calories_burned_estimate or 0, 1),
                "unit": "kcal",
                "session_id": most_calories.id,
                "achieved_at": (
                    most_calories.completed_at.isoformat() if most_calories.completed_at else None
                ),
            },
            {
                "type": "most_exercises",
                "label": "Most exercises completed",
                "value": sum(1 for c in most_completed.exercise_completions if c.completed),
                "unit": "exercises",
                "session_id": most_completed.id,
                "achieved_at": (
                    most_completed.completed_at.isoformat() if most_completed.completed_at else None
                ),
            },
        ]
        return records

    def get_heatmap(self, db: Session, user_id: str, days: int = 365) -> list[dict]:
        """Returns a dict per calendar day for the last `days` days, with the
        session count for that day — consumed by a GitHub-style activity heatmap."""
        sessions = workout_session_repository.list_history_for_user(db, user_id)
        counts: dict[str, int] = defaultdict(int)
        for s in sessions:
            if s.completed_at:
                day_str = self._to_aware(s.completed_at).date().isoformat()
                counts[day_str] += 1

        now_date = datetime.now(UTC).date()
        result = []
        for i in range(days - 1, -1, -1):
            d = (now_date - timedelta(days=i)).isoformat()
            result.append({"date": d, "count": counts.get(d, 0)})
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _to_aware(self, dt: datetime) -> datetime:
        """SQLite stores naive UTC datetimes; treat them as UTC for arithmetic."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    def _compute_streaks(self, sessions: list[WorkoutSession]) -> tuple[int, int]:
        """Current streak (consecutive days including today) and longest ever streak."""
        if not sessions:
            return 0, 0

        # Unique days with a completed session, sorted descending
        workout_dates = sorted(
            {self._to_aware(s.completed_at).date() for s in sessions if s.completed_at},
            reverse=True,
        )
        if not workout_dates:
            return 0, 0

        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)

        # Current streak: start counting only if the most recent workout was today or yesterday
        current = 0
        if workout_dates[0] >= yesterday:
            current = 1
            for i in range(1, len(workout_dates)):
                if (workout_dates[i - 1] - workout_dates[i]).days == 1:
                    current += 1
                else:
                    break

        # Longest ever streak
        longest = 1
        run = 1
        for i in range(1, len(workout_dates)):
            if (workout_dates[i - 1] - workout_dates[i]).days == 1:
                run += 1
                longest = max(longest, run)
            else:
                run = 1

        return current, longest

    def _count_completed_exercises(self, db: Session, user_id: str) -> int:
        """Total exercises marked complete across all sessions ever."""
        result = db.execute(
            select(func.count(ExerciseCompletion.id))
            .join(WorkoutSession, WorkoutSession.id == ExerciseCompletion.workout_session_id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == WorkoutSessionStatus.completed,
                ExerciseCompletion.completed == True,  # noqa: E712
            )
        ).scalar()
        return result or 0
