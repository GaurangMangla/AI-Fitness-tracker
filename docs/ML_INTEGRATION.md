# Athlyt — ML Recommendation Engine Integration (Phase 2.3)

**Status:** Implemented, tested, **and promoted to the production default** (Phase 2.4 — see `ml/models/PRODUCTION_ROLLOUT.md` for the full rollout report). `RECOMMENDATION_ENGINE` now defaults to `"ml"`. The rule engine remains fully intact and unmodified — set `RECOMMENDATION_ENGINE=rule` for an instant rollback with zero code changes (see `ml/models/PRODUCTION_ROLLOUT.md` §7 for the exact procedure).

---

## 1. Architecture

`WorkoutRecommendationService` (unchanged, `app/services/workout_recommendation_service.py`) depends on a `RecommendationEngine` Protocol, not a concrete class:

```python
class RecommendationEngine(Protocol):
    def recommend(self, recommendation_input: RecommendationInput) -> WorkoutSplitDefinition: ...
```

This was the seam `docs/ML_ARCHITECTURE.md` was written around, and it held up exactly as designed — `MLRecommendationService` is a second implementation of this same protocol. Nothing above the engine (routers, schemas, the Workout Planner, the frontend) changed at all.

```
POST /workouts/recommend
        │
        ▼
WorkoutRecommendationService.recommend(profile, workout_days_per_week)
        │
        ▼
self._engine.recommend(recommendation_input)   ← the seam
        │
        ├── RECOMMENDATION_ENGINE=rule  →  RuleBasedRecommendationEngine (unchanged)
        │
        └── RECOMMENDATION_ENGINE=ml    →  MLRecommendationService
                    │
                    ├── success, confidence ≥ threshold → the model's prediction
                    └── ANY failure, or confidence < threshold → RuleBasedRecommendationEngine
```

**Which engine gets constructed is resolved per-request**, via a FastAPI dependency (`app/api/deps.py::get_recommendation_service`), not a module-level singleton built once at import time. This is a deliberate change from how the router worked before this phase — see §2 for why.

---

## 2. Why a per-request dependency, not a singleton

The router previously built `WorkoutRecommendationService()` once, at module import time:

```python
_recommendation_service = WorkoutRecommendationService()  # old
```

This is fine for a single, fixed engine, but breaks the moment the engine needs to depend on an environment variable that can differ between test runs (or, in principle, between requests if a process's settings ever changed) — Python only imports a module once per process, so a module-level singleton would freeze whichever `RECOMMENDATION_ENGINE` value happened to be set the first time `workouts.py` was imported, for the rest of that process's life.

The fix: a factory function, injected via `Depends()`, resolved fresh on every request:

```python
def get_recommendation_service() -> WorkoutRecommendationService:
    settings = get_settings()
    if settings.RECOMMENDATION_ENGINE == "ml":
        return WorkoutRecommendationService(engine=MLRecommendationService())
    return WorkoutRecommendationService()
```

This is cheap to call on every request — constructing either service is just building a small wrapper object; the actual model file is loaded once and cached at the `app/ml/registry` module level (see §3), not reloaded per-request regardless of how many times `get_recommendation_service()` runs.

---

## 3. How the model is loaded

`app/ml/registry.py` loads `model.joblib` and `preprocessor.joblib` **lazily** (on first use, not at process startup) and **caches** both at module level:

```python
def get_model_and_preprocessor() -> tuple[Any, Any]:
    if not _load_attempted:
        _load()
    if _load_error is not None:
        raise ModelLoadError(str(_load_error))
    return _model, _preprocessor
```

**Why lazy, not eager at startup:** importing `app.ml.registry` (which happens indirectly the moment `app.main` is imported, since `deps.py` imports `MLRecommendationService`) must never fail just because the model files happen to be missing — even in an environment where `RECOMMENDATION_ENGINE=rule` and the ML path is never actually exercised. The whole app should boot fine regardless of whether the `.joblib` files are present.

**Why cached, not reloaded per-request:** loading and deserializing a 71MB scikit-learn model is not free — doing it once per process (the first time any request actually needs it) and reusing the in-memory object for every subsequent request is the only sane approach at this scale.

**Model and preprocessor are two separate files, not bundled.** This matches how they were actually exported in `ml/notebooks/train_model.ipynb` — see `ml/ML_TRAINING.md` §6. `docs/ML_ARCHITECTURE.md` §5.6 originally recommended bundling them into one `.joblib` specifically to prevent the two from silently drifting apart. That re-bundling hasn't happened yet; until it does, `app/ml/registry.py` loads them as a matched pair from the same function call and never exposes one without the other, which is the practical mitigation for the same risk in the meantime.

### 3.1 A real bug found and fixed while building this: Git LFS pointer files

`ml/models/model.joblib` and `preprocessor.joblib` are tracked via Git LFS (see the repo's `.gitattributes`). **A plain `git clone` without Git LFS installed checks out a small (~130 byte) plain-text pointer file at that path, not the real model** — the path exists, `Path.exists()` returns `True`, but `joblib.load()` on it fails deep inside pickle's opcode parsing with an opaque `KeyError` (observed during this integration's own development, logged as just the string `"118"` — genuinely useless for diagnosing the real cause).

`app/ml/registry.py` now detects this specific case up front — Git LFS pointer files always start with the literal line `version https://git-lfs.github.com/spec/v1` — and raises a clear, actionable `ModelLoadError` instead:

```
ml/models/model.joblib (or its preprocessor) is a Git LFS pointer file, not the
real model — Git LFS isn't installed or `git lfs pull` was never run.
```

**If you see this in production logs:** run `git lfs install && git lfs pull` on whatever machine/container built the deployment, or check that your hosting platform's build step includes an LFS pull. Render, Railway, and most CI runners need Git LFS explicitly enabled — it is not automatic on a bare `git clone`.

---

## 4. Fallback strategy

Every one of these is caught inside `MLRecommendationService.recommend()` and silently resolved by calling `RuleBasedRecommendationEngine.recommend()` instead — the caller (`WorkoutRecommendationService`, and everything above it) never sees an exception, and the API always returns a normal 200 response.

| Trigger | What happens |
|---|---|
| Model or preprocessor file missing | `ModelLoadError` raised by `registry.py`, caught, logged, falls back |
| Model/preprocessor file is a Git LFS pointer, not the real artifact | Same as above — detected explicitly, clear log message (§3.1) |
| Model/preprocessor file corrupted or unreadable | `joblib.load()` raises, caught, logged, falls back |
| `RecommendationInput` missing `diet_preference`/`height_cm`/`weight_kg` | `build_feature_row()` raises `ValueError`, caught, logged, falls back |
| `predict_proba()` confidence below `ML_CONFIDENCE_THRESHOLD` | No exception — checked explicitly, falls back (this is the "uncertain, not broken" case) |
| Model predicts a class outside the known split keys | Defensive check against a corrupted/mismatched artifact — falls back |
| Any other unexpected exception during prediction | Caught by a broad `except Exception`, logged with the exception, falls back |

**What is never a fallback trigger:** the rule engine itself failing. `RuleBasedRecommendationEngine` has no external dependencies (no file I/O, no model) and is the same code that ran in production before this phase — if it fails, that's a genuine bug in the fallback path itself, not something this phase's fallback logic is designed to catch.

---

## 5. Environment configuration

| Variable | Values | Default | Description |
|---|---|---|---|
| `RECOMMENDATION_ENGINE` | `rule` \| `ml` | **`ml`** | Which engine actually serves `/workouts/recommend` and `/workouts/generate` |
| `ML_MODEL_PATH` | file path | `../ml/models/model.joblib` | Relative to the backend's working directory |
| `ML_PREPROCESSOR_PATH` | file path | `../ml/models/preprocessor.joblib` | Same |
| `ML_CONFIDENCE_THRESHOLD` | `0.0`–`1.0` | `0.6` | Below this `predict_proba()` confidence, defer to the rule engine |

Switching `RECOMMENDATION_ENGINE=rule` in production (rollback) requires **no code change** — set the environment variable on your hosting platform (Render/Railway/Docker) and restart. See §2 for exactly how this takes effect without a module reload, and `ml/models/PRODUCTION_ROLLOUT.md` §7 for the full rollback procedure.

### 5.1 Choosing `ML_CONFIDENCE_THRESHOLD` — now backed by real validation data

`0.6` was originally a deliberately conservative starting point — well above a random-guess baseline for a 5-class problem (`0.2`). It's since been validated against a 500-profile out-of-sample regression test (`ml/models/PRODUCTION_ROLLOUT.md` §4): mean confidence 0.855, median 0.905, with 8.4% of predictions falling below 0.6 (the population the fallback mechanism exists to catch).

**One real finding from that validation worth knowing:** one disagreement had confidence 0.604 — just above threshold, so it would *not* fall back — traced to a profile hitting `recommendation_rules`'s exact `age >= 50` recovery threshold, a sharp rule-engine cutoff the model doesn't reproduce with perfect precision right at the boundary. Raising the threshold to `~0.65` would catch this specific class of edge case while still leaving the large majority of real predictions confidently above it. Not urgent — this is a tuning refinement, not a production incident — but worth doing once there's real traffic to validate against instead of only synthetic data.

---

## 6. Logging

Every recommendation logs its source, and — for ML predictions — confidence, latency, and model version:

```
INFO  Recommendation served by ML model (split=push_pull_legs, confidence=0.940, model_version=v2, latency_ms=3.2)
INFO  ML confidence 0.412 below threshold 0.600, falling back to rule engine (predicted=upper_lower, model_version=v2, latency_ms=2.1)
WARNING  ML recommendation failed, falling back to rule engine (reason=..., model_version=unknown, latency_ms=1.2)
```

`model_version` is read from `ml/models/metadata.json` (written by the training pipeline) — logged as `"unknown"` when the model failed to load at all (so there's nothing to read a version from), and the real version string (e.g. `"v2"`) whenever a load succeeded, regardless of whether that specific request ended up using the ML prediction or falling back on confidence.

No request payloads, no user profile data, and no internal stack traces are ever included in the log message text itself — only the split key, confidence score, latency, and model version, matching the existing logging policy in `app/core/logging_config.py` (nothing sensitive is ever logged). API responses never expose which engine actually served the recommendation, why a fallback happened, or any internal error detail — from the client's perspective, a fallback and a successful ML prediction are indistinguishable, both are just a normal `RecommendationResponse`.

### 6.1 Health check diagnostics

`GET /api/v1/health/detailed` exposes the same information the logs carry (configured engine, model loaded status, model version, confidence threshold) as a point-in-time snapshot — but **only when `DEBUG=true`**, since this is internal operational detail, not something a public health endpoint should show by default. See `ml/models/PRODUCTION_ROLLOUT.md` §3.2 for the exact response shape and the reasoning behind gating it this way.

---

## 7. How to replace the model in the future

1. Retrain in `ml/notebooks/train_model.ipynb` (or a new notebook), following the exact same feature schema documented in `ml/ML_TRAINING.md` §3 — the 19 raw columns in `app/ml/feature_builder.py`'s `_FEATURE_COLUMNS` must stay in sync with whatever the new preprocessor expects.
2. Export the new `model.joblib` and `preprocessor.joblib` to `ml/models/`, overwriting the existing files (or to a new versioned path, updating `ML_MODEL_PATH`/`ML_PREPROCESSOR_PATH` to point at it).
3. If the new model's class labels differ from the current 5 (`full_body`, `home_bodyweight`, `push_pull_legs`, `upper_lower`, `upper_lower_strength`) — e.g. if the `bro_split` dead-code bug documented in `ml/ML_TRAINING.md` §2.4 gets fixed and retrained — no code change is needed here either: `MLRecommendationService` checks the predicted key against `SPLIT_BY_KEY` dynamically, not a hardcoded list.
4. If the **feature schema** changes (a column added, removed, or renamed) — this **does** require updating `app/ml/feature_builder.py`'s `_FEATURE_COLUMNS` and `build_feature_row()` to match, since the `ColumnTransformer` expects an exact column match by name.
5. If the `Equipment` enum ever changes, `feature_builder.py` raises an `AssertionError` at import time (not silently mispredicting) — retrain before deploying a code change that adds/removes an equipment type.
6. Restart the backend process (or redeploy) — `app/ml/registry.py`'s cache is per-process, so a new file at the same path is picked up on the next process start, not hot-swapped into a running process.
7. Consider re-bundling model + preprocessor into a single `.joblib` at this point, per `docs/ML_ARCHITECTURE.md` §5.6's original recommendation — not done in this phase, but worth doing before this becomes a repeated retrain-and-redeploy cycle.

---

## 8. Testing

All ML-specific tests use a **real, tiny** `RandomForestClassifier` + `ColumnTransformer` (trained on a handful of synthetic rows, matching the production feature schema exactly — see `tests/ml_test_helpers.py`), not hand-rolled mock objects with a fake `predict_proba()` method. This means the tests exercise the actual sklearn code paths (`ColumnTransformer.transform()`, `RandomForestClassifier.predict_proba()`) `MLRecommendationService` really calls in production, catching integration bugs a stub would silently hide.

| Test file | Covers |
|---|---|
| `tests/test_ml_registry.py` | Model loading, caching, missing files, corrupted files, Git LFS pointer detection, model version reading, status reporting |
| `tests/test_ml_feature_builder.py` | Feature row construction, correct column order/values, invalid input |
| `tests/test_ml_recommendation_service.py` | Successful prediction, every fallback trigger, logging |
| `tests/test_recommendation_engine_switching.py` | The `RECOMMENDATION_ENGINE` env var (now defaulting to `ml`), rule-engine rollback availability, through the real HTTP API |
| `tests/test_health.py` | Health check's ML diagnostics block and its `DEBUG` gating |

**256 total backend tests, all passing** (203 pre-existing + 33 from the Phase 2.3 integration + 14 from the production rollout + 6 from the `/progress/export` report feature).

Run just the ML-related tests:
```bash
cd backend
pytest tests/test_ml_registry.py tests/test_ml_feature_builder.py tests/test_ml_recommendation_service.py tests/test_recommendation_engine_switching.py tests/test_health.py -v
```

### 8.1 Verifying against the real, trained model (not the test doubles)

The tests above deliberately use a tiny synthetic model so they run fast and don't depend on a 71MB Git LFS artifact being present in CI (see the CI note in §8.2 below — CI now pulls the real LFS files anyway, but the unit tests still use the fast synthetic doubles by design). To verify the actual, real trained model end-to-end:

```bash
cd backend
git lfs pull  # ensure the real model.joblib/preprocessor.joblib are present, not pointer stubs

# RECOMMENDATION_ENGINE=ml is now the default -- no env var needed to opt in.
# To verify the rollback path instead, explicitly set RECOMMENDATION_ENGINE=rule.
uvicorn app.main:app --reload
# then hit POST /workouts/recommend as an authenticated user and confirm
# the response looks sensible, and check the logs for
# "Recommendation served by ML model (split=..., confidence=..., model_version=v2, ...)"
```

### 8.2 CI now validates the real ML path, not just the fallback

`.github/workflows/backend-ci.yml`'s checkout step now sets `lfs: true`. Without this, `ml/models/*.joblib` checks out in CI as small Git LFS pointer files (not the real model), and since `RECOMMENDATION_ENGINE` now defaults to `ml`, every test that doesn't explicitly override the model path would silently exercise only the fallback path — passing, but never actually validating the real prediction path end-to-end in CI. With `lfs: true`, CI now genuinely loads and predicts with the real model on every run.
