"""Schemas for `POST /workouts/recommend`.

Note on `workout_days_per_week`: the spec describes this as a profile field,
but `Profile` (Milestone 1) has no such column, and this milestone is
explicit that existing models must not be modified. Rather than add a column
to an existing, already-deployed table (risky without a migration system —
see `app/main.py`'s `create_all()`-based setup), it's accepted as a request
parameter instead. Every *other* input the spec calls for (goal, experience,
activity level, equipment, age, gender) really does come from the stored
profile, per `WorkoutRecommendationService`.
"""

from pydantic import BaseModel, Field


class WorkoutRecommendationRequest(BaseModel):
    workout_days_per_week: int = Field(
        ge=1, le=7, description="How many days per week the user wants to train."
    )


class RecommendationExplanation(BaseModel):
    """The profile inputs a recommendation was actually based on — shown in
    the frontend's "Why was this recommended?" collapsible section and as
    prediction-detail chips. Human-readable strings (not raw enum values),
    matching the same labels `_build_reason()` already uses in
    `workout_recommendation_service.py`, so the UI's prose and these chips
    never disagree with each other.
    """

    goal: str
    experience: str
    days_per_week: int
    equipment: str
    gender: str
    age: int


class RecommendationResponse(BaseModel):
    title: str
    split_name: str
    workout_days: int
    difficulty: str
    reason: str

    # --- Added for the premium AI recommendation UI (all additive, all
    # defaulted, so any existing caller/test constructing a
    # RecommendationResponse with only the five original fields above keeps
    # working completely unchanged — see workout_recommendation_service.py
    # and ml_recommendation_service.py for how these get populated). ---

    #: Which engine actually produced this recommendation. "ml" or "rule" —
    #: "rule" covers both "RECOMMENDATION_ENGINE=rule" and every automatic
    #: ML-fallback case (missing model, low confidence, etc.), since from
    #: the outside those are indistinguishable: a real, correct rule-engine
    #: recommendation either way. See docs/ML_INTEGRATION.md §4.
    engine: str = "rule"

    #: The model's predict_proba() confidence, 0.0-1.0. `None` whenever
    #: `engine == "rule"` — there is no meaningful confidence figure for a
    #: rule-based decision, and the frontend should hide the confidence UI
    #: entirely rather than show a fabricated number.
    confidence: float | None = None

    #: Wall-clock time the recommendation decision itself took, in
    #: milliseconds. Only shown in development/debug UI, per the frontend
    #: spec — never surfaced to end users as a headline figure.
    latency_ms: float | None = None

    #: The trained model's version string (from ml/models/metadata.json),
    #: e.g. "v2.1". `None` when `engine == "rule"`.
    model_version: str | None = None

    #: The profile inputs behind this specific recommendation — always
    #: populated (goal/experience/days/equipment/gender/age are known
    #: regardless of which engine ran), used for both the "Why this plan?"
    #: explanation and the AI Insights section.
    explanation: RecommendationExplanation | None = None
