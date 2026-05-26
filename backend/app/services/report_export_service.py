"""ReportExportService — compiles a user's full history (weight/body-fat/
sleep logs, body measurements, nutrition logs, workout sessions) into a
downloadable report, as either CSV or PDF.

Kept as its own service rather than bolted onto `ProgressService` because it
reads across three repositories no single existing service already touches
(progress, nutrition, and workout sessions), and because "render a report" is
a distinct concern from the CRUD logic those services own — mixing the two
would make `ProgressService` responsible for reportlab/csv formatting on top
of its actual job (logging and summarizing progress).

CSV needs no extra dependency (stdlib `csv`). PDF uses `reportlab`, imported
lazily inside `build_pdf` so a CSV-only request never pays the cost of
importing it and so the dependency is easy to spot at the one call site that
actually needs it.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.user import User
from app.repositories import nutrition_repository, progress_repository, workout_session_repository

# Report window — a year of history is enough for any real portfolio-scale
# account and keeps the PDF from growing unbounded for a long-lived user.
_HISTORY_LIMIT = 365


class ReportExportService:
    """Stateless — same pattern as the other services in this module."""

    # ------------------------------------------------------------------
    # Data gathering (shared by both formats)
    # ------------------------------------------------------------------

    def _gather(self, db: Session, user: User) -> dict[str, list[Any]]:
        return {
            "progress_logs": progress_repository.list_by_user(db, user.id, limit=_HISTORY_LIMIT),
            "measurements": progress_repository.list_measurements_by_user(
                db, user.id, limit=_HISTORY_LIMIT
            ),
            "nutrition_logs": nutrition_repository.list_logs_by_user(
                db, user.id, limit=_HISTORY_LIMIT
            ),
            "workouts": workout_session_repository.list_history_for_user(db, user.id),
        }

    @staticmethod
    def _display_name(user: User, profile: Profile | None) -> str:
        return profile.name if profile is not None else user.email

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def build_csv(self, db: Session, user: User, profile: Profile | None) -> str:
        data = self._gather(db, user)
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(["Athlyt Progress Report"])
        writer.writerow(["Name", self._display_name(user, profile)])
        writer.writerow(["Email", user.email])
        writer.writerow(["Generated", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")])
        writer.writerow([])

        writer.writerow(["Weight / Body Fat / Sleep Logs"])
        writer.writerow(["Date", "Weight (kg)", "Body Fat (%)", "Sleep (hrs)", "Notes"])
        for lg in data["progress_logs"]:
            writer.writerow(
                [lg.log_date, lg.weight_kg, lg.body_fat_pct, lg.sleep_hours, lg.notes or ""]
            )
        writer.writerow([])

        writer.writerow(["Body Measurements (cm)"])
        writer.writerow(
            ["Date", "Chest", "Waist", "Hips", "Left Arm", "Right Arm", "Left Thigh", "Right Thigh"]
        )
        for m in data["measurements"]:
            writer.writerow(
                [
                    m.log_date,
                    m.chest_cm,
                    m.waist_cm,
                    m.hips_cm,
                    m.left_arm_cm,
                    m.right_arm_cm,
                    m.left_thigh_cm,
                    m.right_thigh_cm,
                ]
            )
        writer.writerow([])

        writer.writerow(["Nutrition Logs"])
        writer.writerow(["Date", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Water (ml)"])
        for lg in data["nutrition_logs"]:
            writer.writerow(
                [lg.log_date, lg.calories_consumed, lg.protein_g, lg.carbs_g, lg.fat_g, lg.water_ml]
            )
        writer.writerow([])

        writer.writerow(["Workout History"])
        writer.writerow(["Completed At", "Duration (min)", "Calories Burned (est.)"])
        for s in data["workouts"]:
            writer.writerow(
                [
                    s.completed_at.strftime("%Y-%m-%d %H:%M") if s.completed_at else "",
                    s.total_duration_minutes,
                    s.calories_burned_estimate,
                ]
            )

        return buf.getvalue()

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def build_pdf(self, db: Session, user: User, profile: Profile | None) -> bytes:
        # Imported lazily — see module docstring.
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        data = self._gather(db, user)
        styles = getSampleStyleSheet()
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            title="Athlyt Progress Report",
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )
        story: list[Any] = []

        story.append(Paragraph("Athlyt Progress Report", styles["Title"]))
        story.append(
            Paragraph(
                f"{self._display_name(user, profile)} &middot; "
                f"generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.25 * inch))

        def add_section(title: str, headers: list[str], rows: list[list[Any]]) -> None:
            story.append(Paragraph(title, styles["Heading2"]))
            if not rows:
                story.append(Paragraph("No data logged yet.", styles["Normal"]))
                story.append(Spacer(1, 0.2 * inch))
                return
            table_data = [headers] + [
                ["" if cell is None else str(cell) for cell in row] for row in rows
            ]
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.25 * inch))

        add_section(
            "Weight / Body Fat / Sleep",
            ["Date", "Weight (kg)", "Body Fat (%)", "Sleep (hrs)"],
            [
                [lg.log_date, lg.weight_kg, lg.body_fat_pct, lg.sleep_hours]
                for lg in data["progress_logs"]
            ],
        )
        add_section(
            "Body Measurements (cm)",
            ["Date", "Chest", "Waist", "Hips", "L.Arm", "R.Arm", "L.Thigh", "R.Thigh"],
            [
                [
                    m.log_date,
                    m.chest_cm,
                    m.waist_cm,
                    m.hips_cm,
                    m.left_arm_cm,
                    m.right_arm_cm,
                    m.left_thigh_cm,
                    m.right_thigh_cm,
                ]
                for m in data["measurements"]
            ],
        )
        add_section(
            "Nutrition Logs",
            ["Date", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Water (ml)"],
            [
                [lg.log_date, lg.calories_consumed, lg.protein_g, lg.carbs_g, lg.fat_g, lg.water_ml]
                for lg in data["nutrition_logs"]
            ],
        )
        add_section(
            "Workout History",
            ["Completed At", "Duration (min)", "Calories Burned (est.)"],
            [
                [
                    s.completed_at.strftime("%Y-%m-%d %H:%M") if s.completed_at else "",
                    s.total_duration_minutes,
                    s.calories_burned_estimate,
                ]
                for s in data["workouts"]
            ],
        )

        doc.build(story)
        return buf.getvalue()
