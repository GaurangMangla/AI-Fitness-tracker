# Athlyt — ML Architecture & Integration Plan (Phase 2, Original Planning Document)

**Status:** This was the original planning document for ML integration, written before any training data existed. The plan described here was followed almost exactly — see [ML_INTEGRATION.md](ML_INTEGRATION.md) for what was actually built, [ml/ML_TRAINING.md](../ml/ML_TRAINING.md) for the dataset generation and training results this plan anticipated.

---

## 1. Current System Review (at time of writing)

### 1.1 How a recommendation flows through the app

```
POST /workouts/recommend  or  POST /workouts/generate
        │
        ▼
WorkoutRecommendationService.recommend(profile, workout_days_per_week)
        │
        ├─ validates profile completeness (raises 422 if incomplete)
        ├─ builds a RecommendationInput dataclass from the profile
        │
        ▼
self._engine.recommend(recommendation_input)   ← THE SEAM
        │
        ▼
RuleBasedRecommendationEngine.recommend()
        │
        ├─ scores all 6 WorkoutSplitDefinition candidates through RULE_PIPELINE
        │  (goal_rule → equipment_rule → experience_rule → workout_days_rule → recovery_rule)
        ├─ filters ineligible candidates
        ├─ picks the highest-scoring eligible one (ties → first defined)
        │
        ▼
WorkoutSplitDefinition  (e.g. "Push Pull Legs", difficulty=intermediate)
        │
        ▼
_build_response() → RecommendationResponse
```

### 1.2 The exact seam this plan targeted

`WorkoutRecommendationService.__init__(self, engine: RecommendationEngine | None = None)` depends on a `Protocol`, not a concrete class:

```python
class RecommendationEngine(Protocol):
    def recommend(self, recommendation_input: RecommendationInput) -> WorkoutSplitDefinition: ...
```

**This means an ML-backed engine is a drop-in replacement by construction — this was designed for exactly this moment.** No router, schema, service call-site, or planner code needed to change to add an ML engine — confirmed true in practice; see [ML_INTEGRATION.md](ML_INTEGRATION.md).

### 1.3 The 6-class target label space

The model's prediction target is one of exactly 6 fixed classes, defined in `app/services/workout_splits.py`: `push_pull_legs`, `upper_lower`, `full_body`, `bro_split`, `upper_lower_strength`, `home_bodyweight`.

**This is a 6-class multiclass classification problem** — a critical decision that shaped every choice below.

---

## 2. ML Architecture

### 2.1 Data flow (end to end, training → inference)

```
┌─────────────────────────────────────────────────────────────────────┐
│  OFFLINE (Google Colab) — training, not part of the running app     │
│                                                                       │
│  Synthetic dataset generation → Feature engineering → Train/val/test │
│  split → Model training + tuning → Evaluation → Export               │
│         (workout_recommender.joblib + metadata.json)                 │
└─────────┼─────────────────────────────────────────────────────────────┘
          │  (manual copy / Git LFS — see ML_INTEGRATION.md)
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ONLINE (FastAPI backend) — inference only, ever                     │
│                                                                       │
│  ml/models/model.joblib, preprocessor.joblib                         │
│         │  loaded once, at first use (see ML_INTEGRATION.md §3)      │
│         ▼                                                             │
│  app/ml/registry.py  →  resolves + loads the model into memory       │
│         │                                                             │
│         ▼                                                             │
│  app/ml/inference/workout_recommender.py                             │
│         │  predict(model, preprocessor, features) -> ModelPrediction │
│         ▼                                                             │
│  MLRecommendationService  (implements RecommendationEngine protocol) │
│         │                                                             │
│         ├─ on success  → WorkoutSplitDefinition                       │
│         └─ on failure  → falls back to RuleBasedRecommendationEngine │
└─────────────────────────────────────────────────────────────────────┘
```

**The backend never trains anything.**

### 2.2 Feature engineering (as planned; matches what was actually trained on)

**Raw inputs**: `age`, `gender`, `height_cm`, `weight_kg`, `fitness_goal`, `activity_level`, `workout_experience`, `equipment_available`, `workout_days_per_week`, `diet_preference`.

**Derived features**: `bmi`, `bmi_category`, `has_gym_access`, `equipment_count`.

**Note on `diet_preference`:** flagged in this original plan as a candidate for feature-importance analysis, since it has no obvious causal relationship to workout-split selection. **Confirmed empirically** after training (see `ml/ML_TRAINING.md` §5.1) — it ranks in the bottom third of feature importance, contributing almost nothing, exactly matching the rule engine's own code (which never reads it).

### 2.3 Encoding strategy

One-hot encoding for categorical fields (`gender`, `fitness_goal`, `activity_level`, `workout_experience`, `diet_preference`, `bmi_category`); multi-hot for `equipment_available` (a user can have multiple equipment types simultaneously); numeric fields passed through unscaled (tree models split on thresholds, not distances).

### 2.4 Model loading strategy (as planned; matches the actual implementation)

```python
# app/ml/registry.py (planned here, implemented in Phase 2.3)
def get_model():
    global _model
    if _model is None:
        _model = joblib.load(settings.ML_MODEL_PATH)
    return _model
```

Loaded once per process, not per-request.

### 2.5 Error handling and fallback (as planned; matches the actual implementation)

This was, and remains, the most important design decision in the whole integration:

```python
class MLRecommendationService:
    def __init__(self):
        self._rule_engine = RuleBasedRecommendationEngine()

    def recommend(self, recommendation_input):
        try:
            ...predict...
            if confidence < CONFIDENCE_THRESHOLD:
                return self._rule_engine.recommend(recommendation_input)
            return SPLIT_BY_KEY[split_key]
        except Exception:
            return self._rule_engine.recommend(recommendation_input)
```

See [ML_INTEGRATION.md](ML_INTEGRATION.md) §4 for the complete, actually-implemented fallback trigger table.

### 2.6 Versioning

Planned convention: `ml/models/workout_recommender/<version>/model.joblib` + `metadata.json`. **Not yet implemented as multiple versions** — the current single `ml/models/model.joblib`/`preprocessor.joblib` pair is the only version that exists. Worth revisiting if/when a retrain happens.

---

## 3. Dataset Schema (as planned; see `ml/ML_TRAINING.md` for what was actually generated)

Synthetic data, generated within realistic physiological and fitness-domain bounds, labeled by directly calling the real `RuleBasedRecommendationEngine` — **exactly as planned here**, confirmed in the actual implementation (`ml/notebooks/generate_dataset.py`).

**A real, unplanned discovery during actual dataset generation:** `bro_split` never occurs in the label space at all — the rule engine can never select it, under any input. This wasn't anticipated in this original planning document; see `ml/ML_TRAINING.md` §2.4 for the full root-cause explanation, discovered empirically, not predicted here.

---

## 4. Model Selection

**Planned and actually used: `RandomForestClassifier`**, over XGBoost/LightGBM/CatBoost/a neural network — reasoning: matches the project's own original architecture plan's stated starting point, no new production dependency, interpretable `feature_importances_`, and the labeling ceiling (a model trained to imitate the rule engine can't exceed the rule engine's own domain knowledge from synthetic data alone) means a fancier algorithm's typical edge on structured data wouldn't have mattered here anyway.

**Actual result:** 98.44% test accuracy, 98.65% macro F1 — see `ml/ML_TRAINING.md` §4-5 for the full evaluation, including the deliberate model-size-vs-accuracy tradeoff made when exporting the final artifact.

---

## 5. Training Pipeline

See `ml/ML_TRAINING.md` for the complete, actual training pipeline — this section of the original plan (Colab notebook structure, preprocessing, train/val/test split, `GridSearchCV` + `StratifiedKFold`, evaluation metrics, `joblib` export) was followed closely; `ML_TRAINING.md` is the authoritative record of what actually happened, including real numbers, not projections.

---

## 6. Backend Integration Design

This section originally sketched `MLRecommendationService` as a planned interface, not yet implemented. **It has since been implemented** — see [ML_INTEGRATION.md](ML_INTEGRATION.md) for the complete, actual design: the real file list, the real fallback logic, the real environment configuration, and one thing this original plan didn't anticipate — the per-request dependency injection change in `app/api/deps.py`, which turned out to be necessary for the environment-variable switching to actually be testable (see ML_INTEGRATION.md §2).

---

## 7. Future Roadmap

1. ~~Planning~~ (this document)
2. ~~Build the synthetic dataset + labeling script, train v1 in Colab~~ — done, see `ml/ML_TRAINING.md`
3. ~~Implement `MLRecommendationService` + registry + inference, wire in behind a feature flag~~ — done, see [ML_INTEGRATION.md](ML_INTEGRATION.md)
4. **Real outcome data**: once enough users have generated plans and either stuck with them or regenerated a different split, use `WorkoutSession` completion/streak data as a genuine outcome-based label — this is the point where ML can actually exceed the rule engine's ceiling, not just imitate it.
5. **`model_predictions` logging table**: log every ML prediction (input features, output, model version, confidence) to the database — enables A/B comparison between model versions after the fact. Would also have caught the v1/rule-engine drift described in item 7 below automatically.
6. **Extend the same pattern to other models**: calorie prediction, weight progress, adherence prediction — this project's `RecommendationEngine` Protocol pattern is a template for how each could get an ML-backed implementation behind the same kind of fallback-safe seam.
7. ~~**Fix the `bro_split` dead-code bug** in the rule engine itself, then retrain~~ — **done**. Fixed in `recommendation_rules.py`, dataset regenerated, model retrained as v2 — see `ml/models/MODEL_COMPARISON.md` for the complete before/after comparison (bro_split: 0% → 0.43% of the dataset, 96% precision / 100% recall on the retrained model; a 150-profile out-of-sample regression test shows 98% raw agreement between the rule engine and v2, 100% effective agreement once the production confidence threshold is accounted for).
8. **Re-bundle model + preprocessor** into a single `.joblib` — see §2.4/§2.5 above and `ML_INTEGRATION.md` §3. Still not done as of v2.

---

## Summary

This document is preserved as the original planning record — comparing it against [ML_INTEGRATION.md](ML_INTEGRATION.md) (what was actually built) and `ml/ML_TRAINING.md` (what was actually trained) shows the plan held up well: the `RecommendationEngine` Protocol seam worked exactly as designed, Random Forest was the right call, and the fallback-first design was carried through faithfully. The two real surprises along the way — `bro_split` being unreachable dead code, and needing per-request dependency injection instead of a module singleton for testable env-var switching — are both documented in their respective implementation docs, not retrofitted into this planning document as if they'd been anticipated.
