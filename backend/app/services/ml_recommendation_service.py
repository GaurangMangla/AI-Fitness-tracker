"""`MLRecommendationService` — an ML-backed implementation of the
`RecommendationEngine` protocol, with a mandatory, automatic fallback to
`RuleBasedRecommendationEngine` on any failure.

See `docs/ML_INTEGRATION.md` for the full design writeup: architecture,
fallback triggers, environment configuration, and how to replace the model
in the future.

The core guarantee this class exists to provide: **a user never sees an
error because the ML model failed.** Every failure mode — missing model
file, corrupted preprocessor, a malformed feature row, a low-confidence
prediction, or a genuinely unexpected exception — is caught here and
silently resolved by deferring to the rule engine instead.
"""

import time

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.ml.feature_builder import build_feature_row
from app.ml.inference.workout_recommender import predict
from app.ml.registry import ModelLoadError, get_model_and_preprocessor, get_model_version
from app.services.recommendation_engine import RuleBasedRecommendationEngine
from app.services.recommendation_types import EngineRecommendation, RecommendationInput
from app.services.workout_splits import SPLIT_BY_KEY, WorkoutSplitDefinition

logger = get_logger(__name__)


class MLRecommendationService:
    """Implements `RecommendationEngine` — same `recommend(RecommendationInput)
    -> WorkoutSplitDefinition` signature as `RuleBasedRecommendationEngine`,
    so `WorkoutRecommendationService` (and everything above it: routers,
    schemas, the Workout Planner, the frontend) needs zero changes to use
    this instead. See `docs/ML_INTEGRATION.md` §1 for the full call chain.

    `recommend()` itself is unchanged from Phase 2.3 — it's now a one-line
    wrapper around `recommend_with_metadata()` (added for the premium AI
    recommendation UI), which contains the exact same logic, exact same log
    messages, and exact same fallback behavior as before. Every existing
    caller and test that only wants the split (not the engine/confidence/
    latency detail) keeps working completely unchanged.
    """

    def __init__(self) -> None:
        # Always constructed, always ready — this is what makes every
        # fallback path below a simple, synchronous method call rather than
        # something that could itself fail.
        self._rule_engine = RuleBasedRecommendationEngine()

    def recommend(self, recommendation_input: RecommendationInput) -> WorkoutSplitDefinition:
        return self.recommend_with_metadata(recommendation_input).split

    def recommend_with_metadata(
        self, recommendation_input: RecommendationInput
    ) -> EngineRecommendation:
        start = time.perf_counter()

        try:
            split_key, confidence = self._predict(recommendation_input)
        except Exception as exc:  # noqa: BLE001 — deliberately broad, see module docstring
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "ML recommendation failed, falling back to rule engine "
                "(reason=%s, model_version=%s, latency_ms=%.1f)",
                exc,
                get_model_version() or "unknown",
                latency_ms,
            )
            return self._fallback(recommendation_input)

        settings = get_settings()
        if confidence < settings.ML_CONFIDENCE_THRESHOLD:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "ML confidence %.3f below threshold %.3f, falling back to rule engine "
                "(predicted=%s, model_version=%s, latency_ms=%.1f)",
                confidence,
                settings.ML_CONFIDENCE_THRESHOLD,
                split_key,
                get_model_version() or "unknown",
                latency_ms,
            )
            return self._fallback(recommendation_input)

        if split_key not in SPLIT_BY_KEY:
            # Defensive: the model should only ever predict one of the
            # classes it was trained on (see ml/models/metadata.json's
            # observed_classes), but a corrupted or mismatched artifact
            # could in principle return something unexpected. Never let an
            # unrecognised key propagate — fall back instead.
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "ML model predicted an unrecognised split key %r, falling back to rule "
                "engine (model_version=%s, latency_ms=%.1f)",
                split_key,
                get_model_version() or "unknown",
                latency_ms,
            )
            return self._fallback(recommendation_input)

        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Recommendation served by ML model (split=%s, confidence=%.3f, "
            "model_version=%s, latency_ms=%.1f)",
            split_key,
            confidence,
            get_model_version() or "unknown",
            latency_ms,
        )
        return EngineRecommendation(
            split=SPLIT_BY_KEY[split_key],
            engine="ml",
            confidence=confidence,
            latency_ms=latency_ms,
            model_version=get_model_version(),
        )

    def _predict(self, recommendation_input: RecommendationInput) -> tuple[str, float]:
        """Raises on any failure — model not loaded, preprocessing error,
        or a genuine prediction error. Never called directly by anything
        outside `recommend_with_metadata()`, which is responsible for
        catching whatever this raises."""
        model, preprocessor = get_model_and_preprocessor()  # raises ModelLoadError
        features = build_feature_row(recommendation_input)  # raises ValueError on bad input
        result = predict(model, preprocessor, features)
        return result.split_key, result.confidence

    def _fallback(self, recommendation_input: RecommendationInput) -> EngineRecommendation:
        return self._rule_engine.recommend_with_metadata(recommendation_input)


__all__ = ["MLRecommendationService", "ModelLoadError"]
