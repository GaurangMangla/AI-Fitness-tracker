"""/progress router."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ValidationError
from app.schemas.progress_nutrition import (
    BodyMeasurementRequest,
    BodyMeasurementResponse,
    ProgressLogRequest,
    ProgressLogResponse,
    ProgressSummaryResponse,
)
from app.services.progress_service import ProgressService
from app.services.report_export_service import ReportExportService

router = APIRouter(prefix="/progress", tags=["progress"])
_svc = ProgressService()
_export_svc = ReportExportService()


@router.post("/logs", response_model=ProgressLogResponse, status_code=status.HTTP_201_CREATED)
def log_progress(body: ProgressLogRequest, current_user: CurrentUser, db: DbSession):
    log = _svc.log_progress(
        db,
        user_id=current_user.id,
        log_date=body.log_date,
        weight_kg=body.weight_kg,
        body_fat_pct=body.body_fat_pct,
        sleep_hours=body.sleep_hours,
        notes=body.notes,
    )
    return ProgressLogResponse.model_validate(log)


@router.get("/logs", response_model=list[ProgressLogResponse])
def get_logs(current_user: CurrentUser, db: DbSession, limit: int = 90):
    logs = _svc.get_logs(db, current_user.id, limit=min(limit, 365))
    return [ProgressLogResponse.model_validate(lg) for lg in logs]


@router.get("/summary", response_model=ProgressSummaryResponse)
def get_summary(current_user: CurrentUser, db: DbSession):
    return _svc.get_summary(db, current_user.id)


@router.post(
    "/measurements",
    response_model=BodyMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_measurement(body: BodyMeasurementRequest, current_user: CurrentUser, db: DbSession):
    m = _svc.log_measurement(
        db,
        user_id=current_user.id,
        log_date=body.log_date,
        chest_cm=body.chest_cm,
        waist_cm=body.waist_cm,
        hips_cm=body.hips_cm,
        left_arm_cm=body.left_arm_cm,
        right_arm_cm=body.right_arm_cm,
        left_thigh_cm=body.left_thigh_cm,
        right_thigh_cm=body.right_thigh_cm,
    )
    return BodyMeasurementResponse.model_validate(m)


@router.get("/measurements", response_model=list[BodyMeasurementResponse])
def get_measurements(current_user: CurrentUser, db: DbSession, limit: int = 30):
    items = _svc.get_measurements(db, current_user.id, limit=min(limit, 100))
    return [BodyMeasurementResponse.model_validate(m) for m in items]


@router.get("/export")
def export_report(current_user: CurrentUser, db: DbSession, format: Literal["csv", "pdf"] = "csv"):
    """Downloadable report combining weight/body-fat/sleep logs, body
    measurements, nutrition logs, and workout history — everything a user
    has logged, in one file. `format=csv` (default) needs no extra
    dependency; `format=pdf` renders the same sections via reportlab.
    """
    date_stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"athlyt-report-{date_stamp}.{format}"

    if format == "pdf":
        content = _export_svc.build_pdf(db, current_user, current_user.profile)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    if format == "csv":
        content = _export_svc.build_csv(db, current_user, current_user.profile)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    raise ValidationError("format must be 'csv' or 'pdf'.")
