"""Runs the trained model against a single feature row and returns a
prediction with its confidence.

Kept separate from `MLRecommendationService` (which owns the fallback
policy) so this module has exactly one job: given a feature DataFrame,
return what the model thinks, with no opinion about confidence thresholds,
logging, or what happens on failure — those are the service's concerns, not
this module's.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ModelPrediction:
    split_key: str
    confidence: float


def predict(model: object, preprocessor: object, features: pd.DataFrame) -> ModelPrediction:
    """Transforms `features` through `preprocessor`, then predicts with
    `model`. Uses `predict_proba` (not just `predict`) specifically to get a
    confidence score — `RandomForestClassifier.predict_proba` returns the
    fraction of trees in the forest that voted for each class, which is
    exactly the "how sure is the model" signal `MLRecommendationService`
    needs for its confidence-threshold fallback logic.

    Raises whatever the underlying sklearn/pandas call raises on malformed
    input — the caller (`MLRecommendationService`) is responsible for
    catching and falling back to the rule engine; this function does not
    swallow errors, so a genuine bug here is never silently hidden as "low
    confidence."
    """
    encoded = preprocessor.transform(features)

    probabilities = model.predict_proba(encoded)[0]
    classes = model.classes_

    best_index = probabilities.argmax()
    return ModelPrediction(
        split_key=str(classes[best_index]),
        confidence=float(probabilities[best_index]),
    )
