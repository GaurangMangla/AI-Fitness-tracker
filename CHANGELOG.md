# Changelog

All notable changes to Athlyt are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- `GET /progress/export?format=csv|pdf` — a downloadable progress report combining weight/body-fat/sleep logs, body measurements, nutrition logs, and workout history into a single file. New `ReportExportService` (`backend/app/services/report_export_service.py`); CSV needs no extra dependency, PDF is rendered via `reportlab` (new backend dependency). Frontend: CSV/PDF export buttons on the Progress page's "Recent logs" section, wired through a new `apiFetchBlob` helper and `useExportReport` hook.
- 6 new backend tests covering both formats, auth, and format validation.

### Planned
- Progress photo upload (S3/R2 object storage)
- Push notifications / reminders
- AI coach chatbot (LLM-backed conversation)
- Refresh-token rotation (currently a single 7-day access token)
- Tune `ML_CONFIDENCE_THRESHOLD` upward (~0.65) based on an edge case found during the production rollout validation (see `ml/models/PRODUCTION_ROLLOUT.md` §4.4)
- Re-bundle `model.joblib` + `preprocessor.joblib` into a single artifact

---

## [1.3.0] — Production Rollout: ML as the Default Recommendation Engine

### Changed
- `RECOMMENDATION_ENGINE` default: `"rule"` → `"ml"` — the ML model now serves `POST /workouts/recommend` and `/workouts/generate` by default in production. The rule engine remains fully intact, unmodified, and available as an instant, zero-code-change rollback (`RECOMMENDATION_ENGINE=rule`).
- `GET /api/v1/health/detailed` now includes a `recommendation_engine` diagnostics block (configured engine, model loaded status, model version, confidence threshold) — gated behind `DEBUG=true`, hidden otherwise.
- Every ML recommendation log line now includes `model_version`, read from `ml/models/metadata.json`.
- `.github/workflows/backend-ci.yml` now pulls Git LFS objects on checkout — without this, CI would only ever exercise the fallback path now that ML is the default, never validating the real model end-to-end.

### Added
- `app/ml/registry.py`: `get_model_version()` and `get_status()` — expose the registry's load state for the health check without ever triggering a load themselves.
- `ml/models/PRODUCTION_ROLLOUT.md` — the master validation report for this rollout: 500-profile out-of-sample regression test (99.2% raw agreement, 99.8% effective agreement with fallback), full performance benchmarks (cold start, warm latency, memory, CPU, leak check), and rollback instructions.
- 11 new backend tests covering the new default, the rollback path, model version reporting, and health check gating.

### Fixed
- Two real, pre-existing stale-filename bugs found while reviewing production configuration: `backend/.env.example` and `docker-compose.yml` both still referenced `workout_recommender.joblib` (a file that was never actually produced by training) instead of the real `model.joblib`/`preprocessor.joblib` — same class of bug fixed in `config.py` during Phase 2.3, but missed in these two files at the time.
- `docker-compose.yml` was completely missing `ML_PREPROCESSOR_PATH` and `RECOMMENDATION_ENGINE` from the backend service's environment — added with correct container-relative paths.
- `DEPLOYMENT.md` had a stale test count (220) and an `ML_MODEL_PATH` description claiming it was "currently unused by any endpoint" — long untrue since Phase 2.3.

### Investigated
- One disagreement in the 500-profile regression test had ML confidence (0.604) just above the production threshold, meaning it would not fall back. Root-caused to a profile at exactly `age=50` — the hard threshold in `recommendation_rules.recovery_rule` — which the tree-based model doesn't reproduce with perfect precision right at the boundary. Documented as a genuine, minor, explainable limitation with a concrete tuning recommendation, not treated as a bug.
- Confirmed via a 5,000-prediction benchmark that there is no memory leak in the inference path — memory plateaus after the first 1,000 predictions and stays flat.

Backend tests: 250 (was 239).

---

## [1.2.0] — Fix `bro_split` and Retrain the Model (v2)

### Fixed
- `bro_split` was structurally unreachable in the rule engine under any input — `recommendation_rules.py`'s advanced-experience score for `bro_split` (`10`) was never enough to overcome `push_pull_legs`'s goal-score lead in any `FitnessGoal`. Raised to `12`, verified mathematically across every goal × day-count combination before touching code, then confirmed live: `bro_split` now wins at its real-world niche (advanced experience, 5 days/week, full gym) across every goal, while `push_pull_legs` still correctly wins at 6 days.

### Added
- 3 new regression tests locking in the fix and confirming no other split's behavior changed.
- Retrained the ML model (v2) against the fixed rule engine: regenerated the 100k-row synthetic dataset (same generator, same seed — only the rule engine's fix changed the output), retrained with the identical pipeline and hyperparameters as v1. `bro_split` now genuinely present (0.43% of the dataset) and correctly predicted (96% precision, 100% recall on 65 held-out test cases). Every other class's performance stayed within noise of v1.
- `ml/models/MODEL_COMPARISON.md` — full v1-vs-v2 comparison: dataset diff, model metrics, per-class changes, a 150-profile out-of-sample rule-vs-ML regression test (98% raw agreement, 100% effective agreement with the confidence-threshold fallback).

Backend tests: 239 (was 236).

---

## [1.1.0] — Machine Learning: Dataset, Training, and Backend Integration

### Added
- **Dataset generation** (`ml/notebooks/generate_dataset.py`): 100,000 synthetic user profiles, labeled by directly calling the real, deployed `RuleBasedRecommendationEngine` — not an approximation of its logic. Realistic distributions verified against spec (age 16-65, beginner majority, bodyweight more common than full gym, balanced goals, weight correlated with height via BMI).
- **Model training** (`ml/notebooks/train_model.ipynb`): `RandomForestClassifier`, `GridSearchCV` + `StratifiedKFold`, 98.44% test accuracy, 98.65% macro F1. Deliberately traded ~1 point of accuracy for a 3.4× smaller model file (71MB vs. an unconstrained-depth config's 241MB).
- **Backend integration**: `MLRecommendationService` implements the existing `RecommendationEngine` Protocol — zero changes needed to any router, schema, the Workout Planner, or the frontend. Automatic fallback to the rule engine on every failure mode (missing/corrupted model, low confidence, invalid input, unrecognised prediction, any unexpected exception).
- `RECOMMENDATION_ENGINE=rule|ml` environment variable (defaulting to `rule` at this point) switches implementations with zero code changes.
- `docs/ML_ARCHITECTURE.md` (original planning document) and `docs/ML_INTEGRATION.md` (the actual implementation writeup).
- `ml/ML_TRAINING.md` — full dataset generation, training pipeline, and evaluation writeup.

### Fixed
- `ML_MODEL_PATH`'s default pointed to a file (`workout_recommender.joblib`) that training never actually produced — fixed to `model.joblib`, with a matching `ML_PREPROCESSOR_PATH` added.
- Git LFS pointer files (present on any `git clone` without `git lfs pull`) previously caused a cryptic `KeyError` when `joblib.load()` tried to unpickle the plain-text stub — now detected explicitly with a clear, actionable error message.
- Router's recommendation service was a module-level singleton, built once at import time — replaced with a per-request `Depends()` factory, required for the `RECOMMENDATION_ENGINE` environment variable to actually be testable and effective.

### Discovered (not yet fixed at this point — see 1.2.0)
- `bro_split` never appears in the dataset — verified exhaustively that the rule engine can never select it under any input. Documented, not fixed, since fixing the rule engine was out of scope for this phase.

Backend tests: 236 (was 203).

---

## [1.0.0] — Live Production Deployment

### Added
- Deployed live: frontend on Vercel, backend on Render, database on Neon PostgreSQL
- Comprehensive root-level `DEPLOYMENT.md` — codebase-specific step-by-step guide covering Render/Vercel/Neon setup, environment variable reference, security review, custom domain + SSL setup, pre-deployment testing checklist, post-deployment verification checklist, and a 20-item troubleshooting table

### Fixed
- Ruff/black version drift between local dev and CI — pinned both to exact versions (`ruff==0.15.20`, `black==25.12.0`) after a newer CI-resolved ruff version flagged `UP042` (str+Enum pattern) and a newer black reformatted an Alembic-generated migration file that had never been run through black
- Ignored `UP042` explicitly in `ruff` config — the project deliberately uses `(str, Enum)` throughout `app/models/enums.py` for SQLAlchemy compatibility, not `StrEnum`

---

## [0.5.0] — Production Readiness (Backend Hardening)

### Added
- `app/core/logging_config.py` — structured logging, DEBUG in local/test, INFO in production, correctly scoped so `app.*` loggers propagate to root without duplicate output
- `app/core/security_headers.py` — `SecurityHeadersMiddleware` adding baseline security headers to every API response
- `TrustedHostMiddleware` + `ALLOWED_HOSTS` setting — rejects requests with an unrecognized `Host` header
- Dedicated Neon PostgreSQL section in deployment docs (SSL requirement, autosuspend behavior, connection limits)
- `docker-compose.yml`, `docker-compose.override.yml` — full local stack (postgres + backend + frontend) with dev-mode hot reload
- `backend/Dockerfile`, `frontend/Dockerfile` (+ `Dockerfile.dev`) — multi-stage production builds
- GitHub Actions CI — `backend-ci.yml` (pytest/ruff/black) and `frontend-ci.yml` (install/lint/build), path-filtered and cached

### Fixed
- **Silent unhandled exceptions** — registering a custom `Exception` handler had replaced Starlette's default traceback-logging middleware; every unhandled 500 was previously invisible in logs. Fixed with explicit `logger.exception(...)`.
- Alembic migration file's trailing whitespace (auto-generated, never previously run through `black`)

### Changed
- `app/main.py` — `create_all()` now only runs in `local`/`test` environments; production schema is managed exclusively by Alembic

---

## [0.4.1] — Alembic & PostgreSQL Migration Readiness

### Added
- Alembic initialized — `alembic/env.py` supports both SQLite (dev/test) and PostgreSQL (production) from the same codebase, with `render_as_batch=True` for SQLite ALTER support and `compare_type=True` for enum change detection
- Initial migration (`alembic/versions/..._initial_schema.py`) covering all 13 tables, every FK with CASCADE rules, every index, all `native_enum=False` enums
- PostgreSQL connection pool tuning in `app/db/session.py` (`pool_pre_ping`, `pool_size`, `pool_recycle`) — handles free-tier database autosuspend gracefully

---

## [0.4.0] — Production Audit & Polish

### Added
- `docs/` folder: ARCHITECTURE.md, DATABASE_SCHEMA.md, DEPLOYMENT.md, API_REFERENCE.md, PROJECT_BIBLE.md, CHANGELOG.md
- `loading.tsx` for every app route (Next.js App Router loading UI)
- `error.tsx` app-level error boundary with retry
- `not-found.tsx` 404 page with ambient background
- `GET /api/v1/health/detailed` extended health check endpoint
- Security headers in `next.config.ts` (X-Content-Type-Options, X-Frame-Options, etc.)
- Proper TypeScript types for all API responses — eliminated `eslint-disable any` from pages
- Dedicated `hooks/use-dashboard-data.ts` for progress, nutrition, and stats hooks
- `reactStrictMode: true` in Next.js config

### Fixed
- Settings page `SelectField` was re-created on every render (moved outside component)
- Progress/nutrition/workouts pages used inline `useQuery` hooks (extracted to `use-dashboard-data.ts`)
- `pyproject.toml` version pins were too narrow (would block installs in ~12 months)
- CRLF trailing bytes in `config.py`
- Missing `htmlFor` attributes on form labels in progress and nutrition pages

### Changed
- Version pins loosened from patch-level to minor-level compatibility

---

## [0.3.0] — Complete Feature Set

### Added
- **Progress module**: weight/body-fat/sleep logging (upsert), body measurements, 30-day change summary, weight trend chart
- **Nutrition module**: rule-based meal plan generation (non-veg/vegetarian/vegan + Indian templates), daily macro logging, weekly summary
- **Workout statistics**: total sessions, total minutes, current/longest streak, weekly volume, personal records, 365-day activity heatmap
- **Sidebar navigation** (desktop) + bottom nav (mobile)
- **/workouts page**: stats dashboard + history + today's workout
- **/progress page**: weight chart (Recharts), log form, history table
- **/nutrition page**: macro donut chart, meal cards, daily log form
- **/settings page**: full profile edit with all onboarding fields

---

## [0.2.0] — Workout Tracking + Dynamic UI

### Added
- `WorkoutSession` and `ExerciseCompletion` models
- Full session lifecycle: start → complete/skip exercises → pause/resume → finish
- Accurate duration tracking (`accumulated_active_seconds` — excludes paused time)
- MET-based calorie burn estimate
- Workout history (permanent append-only)
- `POST /workouts/start`, `/{id}/pause`, `/{id}/resume`, `/{id}/exercise/{eid}/complete`, `/{id}/exercise/{eid}/skip`, `/{id}/finish`
- `GET /workouts/history`, `GET /workouts/history/{id}`
- **Active workout card**: live timer, animated progress bar, exercise checklist, finish screen
- **Cursor-following glow** (60fps via `requestAnimationFrame`)
- **Ambient gradient orbs** (4 slow-drifting, CSS animation)
- **SVG noise texture** overlay
- **3D perspective tilt cards** with inner spotlight
- `TiltCard` and `AmbientBackground` shared components

---

## [0.1.0] — Foundation

### Added
- Monorepo: `frontend/`, `backend/`, `ml/`
- **Auth**: register, login, JWT (7-day), bcrypt password hashing
- **Profile & onboarding**: multi-field onboarding, BMI, Mifflin-St Jeor calorie estimate
- **Exercise library**: 100 exercises across 7 muscle groups, idempotent seeding
- **Workout recommendation engine**: modular rule-based split selection (PPL, Upper/Lower, Full Body, Bro Split, Home)
- **Workout planner**: dynamic exercise selection from DB, weekly plan generation, plan persistence
- **Dashboard**: welcome card, today's workout, weekly plan grid, exercise detail
- Repository Pattern + Service Layer architecture
- 214 backend tests (pytest)
- Ruff + Black linting
- Responsive layout, dark mode, Framer Motion animations
- `DashboardStatCard`, `GlassCard`, `SectionHeader`, `PrimaryButton` shared components

---

## [1.3.1] — Fix scikit-learn Version Conflict

### Fixed
- `model.joblib`/`preprocessor.joblib` were originally pickled with scikit-learn 1.9.0, triggering `InconsistentVersionWarning` in any environment resolving an older, more common version (e.g. 1.5.2). An initial fix attempt pinned `pyproject.toml` to exactly `scikit-learn==1.9.0` — this backfired in a real environment, conflicting with `sklearn-compat` (a transitive dependency of another installed package), which requires `scikit-learn<1.9`.
- Corrected by retraining the model (v2.1) with `scikit-learn==1.5.2` — same dataset, same seed, same hyperparameters as v2, only the library version differs — and tightening `pyproject.toml`'s constraint to `scikit-learn>=1.5,<1.9` (respecting the real-world `sklearn-compat` conflict, not just picking an arbitrary exact version).
- Retrained model verified to load with zero scikit-learn version-mismatch warnings, and performs at least as well as v2 (99.40% test accuracy, 99.45% macro F1, `bro_split` at 98% precision / 100% recall — all comparable-or-better than v2's numbers).

Backend tests: 250 (unchanged) — this was a dependency/environment fix, not a feature or behavior change.
