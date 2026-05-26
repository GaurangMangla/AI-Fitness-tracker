"""Types passed through the recommendation rule pipeline.

Kept separate from `workout_recommendation_service.py` so the engine module
(`recommendation_engine.py`, `recommendation_rules.py`) has no dependency on
the service layer or on FastAPI/Pydantic at all — it only knows about plain
dataclasses. That's what makes it trivial to call from a script or a future
ML training pipeline without dragging the web framework along.
"""

from dataclasses import dataclass, field

from app.models.enums import (
    ActivityLevel,
    DietPreference,
    Equipment,
    FitnessGoal,
    Gender,
    WorkoutExperience,
)
from app.services.workout_splits import WorkoutSplitDefinition


@dataclass(frozen=True)
class RecommendationInput:
    """Everything a rule might need, gathered once up front.

    `gender` is included for a complete input contract (the spec calls for
    it as an input) even though no current rule uses it — see
    `recommendation_rules.recovery_rule` for why.

    `diet_preference`, `height_cm`, and `weight_kg` are optional, ML-only
    additions (Phase 2.3): the rule engine has never needed them, but the
    trained model was fit on features including all three (see
    `ml/ML_TRAINING.md` §3). Added here — rather than changing the
    `RecommendationEngine` protocol signature, or threading a separate
    `Profile` argument through it — specifically so `MLRecommendationService`
    can implement the exact same `recommend(RecommendationInput) ->
    WorkoutSplitDefinition` interface the rule engine already does, per this
    phase's explicit requirement to accept "the same input currently passed
    to the RuleBasedRecommendationEngine." Defaulting to `None` means every
    existing caller and test that constructs this dataclass without them
    keeps working unchanged; the rule engine simply never reads them, the
    same way it already never reads `gender`.
    """

    fitness_goal: FitnessGoal
    workout_experience: WorkoutExperience
    activity_level: ActivityLevel
    equipment_available: list[Equipment]
    workout_days_per_week: int
    age: int
    gender: Gender
    diet_preference: DietPreference | None = None
    height_cm: float | None = None
    weight_kg: float | None = None


@dataclass
class ScoredSplit:
    """One candidate split's running score as it passes through the rule
    pipeline. Mutated in place by each rule — simpler than threading
    immutable copies through five functions, and nothing here is shared
    across requests so there's no concurrency concern."""

    definition: WorkoutSplitDefinition
    score: float = 0.0
    eligible: bool = True
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EngineRecommendation:
    """A recommendation *plus* the metadata about how it was produced —
    which engine, how confident it was, how long it took, which model
    version. Added for the "Premium AI Recommendation Experience" phase so
    the frontend can show this to users, without changing the existing
    `RecommendationEngine.recommend(RecommendationInput) ->
    WorkoutSplitDefinition` protocol method at all (see
    `recommendation_engine.py` and `ml_recommendation_service.py` —
    `.recommend()` on both engines is completely unchanged; each gained a
    new, additional `recommend_with_metadata()` method instead that wraps
    the exact same underlying logic).

    `confidence` and `model_version` are `None` for the rule engine — it
    has no probabilistic notion of confidence, and no model version to
    report. The frontend is expected to hide those fields when `engine ==
    "rule"` rather than show a fake/placeholder number.
    """

    split: WorkoutSplitDefinition
    engine: str  # "ml" | "rule"
    confidence: float | None
    latency_ms: float
    model_version: str | None
