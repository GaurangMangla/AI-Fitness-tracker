# Athlyt — Architecture

## System overview

Athlyt is a **modular monolith** with a clean service-layer boundary that makes individual modules independently testable and extractable later if scale demands it.

```
Browser → Next.js 15 (SSR first load, client fetch after)
        → FastAPI /api/v1/...
        → Service Layer
        → Repository Layer
        → SQLAlchemy ORM
        → SQLite (dev) / PostgreSQL (prod)
```

## Backend layers

```
Router  (app/api/v1/routers/)   — thin: parse request, call one service, return response
   ↓
Service (app/services/)         — owns all business logic; calls repositories + other services
   ↓
Repository (app/repositories/)  — the only layer that touches SQLAlchemy sessions
   ↓
ORM Model (app/models/)         — SQLAlchemy 2.0 declarative; Mapped[] typed columns
   ↓
Database                        — SQLite (dev), PostgreSQL-compatible schema design
```

**Rules enforced throughout:**
- Routers never query the database directly.
- Services never import from routers.
- Repositories are the only files that import SQLAlchemy's `Session`.
- ORM models are never returned over the API — always serialized through Pydantic schemas.

## Frontend layers

```
Page (app/(app)/*)              — data orchestration, layout, state
   ↓
Hook (hooks/)                   — TanStack Query wrappers; typed API calls
   ↓
Component (components/)         — presentational; receives typed props
   ↓
API Client (lib/api-client.ts)  — single fetch wrapper; attaches JWT; extracts error message
```

## Module map

| Domain | Backend service | Frontend hook | API prefix |
|---|---|---|---|
| Auth | `auth_service` | `handleAuthSuccess` | `/auth` |
| Users/Profile | `user_service` | `useCurrentUser` | `/users` |
| Exercises | `exercise_service` | — | `/exercises` |
| Workout planning | `workout_recommendation_service`, `workout_planner_service` | `useWorkouts`, `useGenerateWorkout` | `/workouts` |
| Workout tracking | `workout_tracking_service` | `useWorkoutSession` | `/workouts` |
| Workout stats | `workout_stats_service` | `useWorkoutStats`, `useWorkoutHistory` | `/workouts/stats` |
| Progress | `progress_service` | `useProgressSummary`, `useProgressLogs` | `/progress` |
| Nutrition | `nutrition_service` | `useNutritionPlan`, `useLogNutrition` | `/nutrition` |

## Key design decisions

### Why a monolith (not microservices)?
At this scale and team size (one developer), microservices add operational overhead — separate deploys, network hops, distributed tracing — with no corresponding benefit. The service-layer boundaries are clean enough that extracting, say, the nutrition service into its own process later is a well-defined operation. The architecture tells a credible story: "I chose a monolith deliberately and designed the boundaries so the extraction point is clear."

### Why synchronous SQLAlchemy (not async)?
FastAPI runs synchronous dependency functions in a threadpool automatically, so `await session.execute(...)` and `session.execute(...)` have identical request-handling characteristics at this scale. Async SQLAlchemy adds: an async engine, an async session factory, async Alembic env setup, and a category of subtle bugs (mixing sync and async calls) — none of which pay off here.

### Why SQLite in dev / PostgreSQL-compatible schema?
- UUIDs stored as `String(36)` — SQLite has no native UUID type; `String(36)` works identically on Postgres once the `DATABASE_URL` is changed.
- Enums stored as `VARCHAR` with `native_enum=False` — avoids Postgres's ALTER TYPE for enum changes.
- No SQLite-specific syntax anywhere — only SQLAlchemy ORM constructs used.
- Switching is a one-line `DATABASE_URL` change + `pip install psycopg2-binary`.

### Why no Alembic yet?
`Base.metadata.create_all()` on startup handles schema creation correctly for a project with no production database yet. Alembic earns its keep when you have a live database with real user data that a migration must not lose. The decision should be made before the first real deployment, not before.

### Why localStorage for the JWT (not httpOnly cookie)?
httpOnly cookies require the Next.js server to participate in auth (middleware-level redirects, cookie-setting API routes). The entire frontend is deployed statically to Vercel — adding a server component purely for cookie handling would change the deployment model. The single 7-day JWT (not a long-lived refresh token) caps the XSS risk window. The tradeoff is documented in `frontend/lib/auth-token.ts`.

### Why rule-based generation (not ML) for workouts and nutrition?
The workout recommendation engine uses a modular scoring pipeline (not a monolithic if/else chain) designed with a `RecommendationEngine` protocol so a `SklearnWorkoutRecommender` can be swapped in by changing one line in `workout_recommendation_service.py`. The ML model is trained separately in Colab and loaded via `joblib` — the inference layer is already wired (`app/ml/`), just waiting for a trained artifact.

## Security

- **Passwords** — bcrypt directly (not passlib, which is incompatible with bcrypt 4.x+).
- **JWT** — PyJWT, HS256, 7-day expiry. `auto_error=False` on HTTPBearer ensures 401 (not 403) for missing tokens.
- **CORS** — explicit origin list via `CORS_ORIGINS` env var; `NoDecode` prevents pydantic-settings from JSON-parsing it.
- **Input validation** — Pydantic v2 on every request body; `email-validator` on email fields.
- **Error messages** — domain exceptions map to HTTP status codes in one place (`exception_handlers.py`); unhandled exceptions return a generic 500 with no internal details.
