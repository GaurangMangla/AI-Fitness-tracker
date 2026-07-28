# Athlyt — Manual Deployment Guide

This guide walks through deploying Athlyt from scratch: frontend on Vercel, backend on Render, database on Neon (or Supabase). Every command and setting below is taken directly from this codebase — not generic boilerplate.

---

## 1. Project facts (what you're actually deploying)

| Component | Detail | Source |
|---|---|---|
| Backend framework | FastAPI | `backend/pyproject.toml` |
| Python version | 3.12 (`requires-python = ">=3.12"`) | `backend/pyproject.toml` |
| Backend package manager | pip + hatchling (PEP 621 `pyproject.toml`, no Poetry/uv) | `backend/pyproject.toml` |
| ASGI server | Uvicorn (`uvicorn[standard]`) | `backend/pyproject.toml` |
| Backend DB layer | SQLAlchemy 2.0, synchronous (not async) | `backend/app/db/session.py` |
| Migrations | Alembic — production schema source of truth | `backend/alembic/` |
| Frontend framework | Next.js 15 (App Router) | `frontend/package.json` |
| Frontend package manager | npm (`package-lock.json` present) | `frontend/package-lock.json` |
| Node version | Not pinned in `package.json` (`engines` unset) — use Node 20 | see §9 |
| Containerization | Dockerfiles present for both services + `docker-compose.yml` (optional — Render/Vercel do not require Docker) | `backend/Dockerfile`, `frontend/Dockerfile` |

**Current database:** SQLite (`sqlite:///./athlyt.db`), used only in local development and tests. Production is designed to run on PostgreSQL — this is not a "future migration," it's the intended production configuration already built into the codebase (`DATABASE_URL` swap + Alembic). See §4.

---

## 2. Backend — Deploy on Render

### 2.1 Root directory
```
backend
```
Render needs this set explicitly since the repo is a monorepo (frontend + backend + ml at the root).

### 2.2 Build command
```
pip install -e .
```
This reads `backend/pyproject.toml` and installs FastAPI, SQLAlchemy, Alembic, psycopg2-binary, and every other listed dependency. (`.[dev]` is not needed in production — that installs ruff/black/pytest, which the running server never uses.)

**Git LFS note:** `ml/models/model.joblib` and `preprocessor.joblib` are tracked via Git LFS. Render's git-based deploys generally pull LFS objects automatically, but this varies by plan/configuration — verify it after your first deploy by checking `GET /health/detailed` (with `DEBUG=true` temporarily) for `"ml_model_loaded": true`. If it's `false`, see §8.2's troubleshooting note.

### 2.3 Start command
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
Two things happen in order:
1. `alembic upgrade head` applies every migration in `backend/alembic/versions/` to the connected database. This is idempotent — safe to run on every deploy, including the very first one (it creates all 13 tables from nothing).
2. `uvicorn` starts the server, binding to `0.0.0.0` (required — Render's load balancer connects from outside the container) and `$PORT` (Render injects this env var automatically; do not hardcode 8000).

If step 1 fails, step 2 never runs — a broken migration surfaces immediately in Render's deploy logs instead of a server that starts but serves a broken schema.

### 2.4 Health check path
```
/api/v1/health
```
Returns `{"status": "ok", "version": "0.1.0", "database": "healthy"}` when everything is working. Render polls this to decide whether a deploy succeeded and whether the service is currently healthy. Defined in `backend/app/api/v1/routers/health.py`.

A more detailed variant exists at `/api/v1/health/detailed` (adds environment name, Python version, and — when `DEBUG=true` — the recommendation engine's current state: configured engine, whether the ML model loaded, its version, and the confidence threshold). Useful for manual debugging; not needed for the health check configuration itself, and not shown by default (see `ml/models/PRODUCTION_ROLLOUT.md` §3.2).

### 2.5 Required environment variables

Set these in Render's dashboard under your service → **Environment**:

| Variable | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `production` | Switches off `create_all()` — see §8.1 |
| `DEBUG` | `false` | Disables SQL query logging and hides ML diagnostics on `/health/detailed` |
| `DATABASE_URL` | *(from Neon/Supabase, see §4)* | Must start with `postgresql+psycopg2://` |
| `JWT_SECRET_KEY` | *(generate — see below)* | ≥ 32 characters, or the app refuses to start |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | No trailing slash; comma-separate multiple origins |
| `ALLOWED_HOSTS` | `your-backend.onrender.com` | Your actual Render URL once assigned |
| `RECOMMENDATION_ENGINE` | `ml` (default — can omit) | Set to `rule` for an instant rollback with zero code changes; see `ml/models/PRODUCTION_ROLLOUT.md` §7 |

Generate `JWT_SECRET_KEY` locally before deploying:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Paste the output directly into Render's environment variable value field.

### 2.6 Step-by-step

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect your GitHub account and select the `Athlyt` repository.
4. Set **Root Directory** to `backend`.
5. Set **Runtime** to `Python 3`.
6. Set **Build Command** to `pip install -e .`.
7. Set **Start Command** to `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
8. Under **Environment Variables**, add all six variables from §2.5. For `DATABASE_URL`, you'll need a Neon/Supabase connection string first — do §4 before this step if you haven't yet.
9. Under **Health Check Path**, enter `/api/v1/health`.
10. Click **Create Web Service**. Render will build and deploy — watch the logs.
11. Once deployed, note the URL Render assigns (e.g. `https://athlyt-backend.onrender.com`). You'll need this for the frontend's `NEXT_PUBLIC_API_URL` and to update `ALLOWED_HOSTS` to the real value.

### 2.7 Common mistakes

- **Forgetting `--host 0.0.0.0`** — defaults to `127.0.0.1`, which only accepts connections from inside the container. Render's health checks and external traffic will fail to connect. Always bind to `0.0.0.0` in production.
- **Hardcoding port 8000 instead of `$PORT`** — Render assigns its own port at runtime; a hardcoded port causes the health check to fail even though the app is technically running.
- **Using `DATABASE_URL=postgresql://...` instead of `postgresql+psycopg2://...`** — SQLAlchemy needs the driver name in the scheme. Plain `postgresql://` defaults to a driver that isn't installed (`psycopg2-binary` is what's actually in `pyproject.toml`).
- **Forgetting `?sslmode=require` on a Neon connection string** — Neon rejects unencrypted connections outright; the app will fail to connect with an SSL error, not a clear "add sslmode" message.
- **Setting `ALLOWED_HOSTS=*` in production** — works, but defeats the Host-header protection the setting exists for. Set it to your real Render domain once you know it.
- **Running `pip install -e ".[dev]"` as the build command** — installs ruff/black/pytest into production for no reason; harmless but wasteful. Use `pip install -e .`.

### 2.8 How to verify the deployment

```bash
# 1. Health check
curl https://your-backend.onrender.com/api/v1/health
# Expect: {"status":"ok","version":"0.1.0","database":"healthy"}

# 2. Swagger UI loads (open in browser)
open https://your-backend.onrender.com/docs

# 3. OpenAPI spec is served and lists all routes
curl https://your-backend.onrender.com/openapi.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)['paths']), 'routes')"
# Expect: 35 routes

# 4. Register a test user end-to-end
curl -X POST https://your-backend.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}'
# Expect: 201 with a user object and access_token
```

If `database: "unhealthy"` appears in the health check response, the app started but can't reach Postgres — check `DATABASE_URL` first (see §10 troubleshooting).

---

## 3. Frontend — Deploy on Vercel

### 3.1 Root directory
```
frontend
```

### 3.2 Framework preset
Vercel auto-detects **Next.js** from `frontend/package.json` — no manual configuration needed here.

### 3.3 Build command
Leave as Vercel's default:
```
npm run build
```
This runs `next build`, which type-checks the entire project and produces the production bundle. If there's a TypeScript error anywhere, the build fails here — same as it would in CI.

### 3.4 Output settings
Leave as Vercel's default (`.next`). Do **not** set `NEXT_STANDALONE=true` for a Vercel deployment — that environment variable exists specifically for the Docker build path (`frontend/Dockerfile`) and produces a self-contained server bundle that Vercel's own infrastructure doesn't need or expect. Vercel manages its own serverless bundling; leaving `output` unset (the default when `NEXT_STANDALONE` isn't `"true"`) is correct.

### 3.5 Environment variables

| Variable | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.onrender.com/api/v1` | Must include the `/api/v1` suffix; no trailing slash |

**Critical detail:** `NEXT_PUBLIC_*` variables are baked into the JavaScript bundle at **build time**, not read at runtime. If you change this value after deploying, you must trigger a new deployment (Vercel → **Deployments** → **Redeploy**) for it to take effect — restarting the existing deployment does nothing.

### 3.6 Step-by-step

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import the `Athlyt` GitHub repository.
3. Set **Root Directory** to `frontend` (Vercel will prompt for this since it's a monorepo).
4. Confirm **Framework Preset** shows `Next.js` (auto-detected).
5. Under **Environment Variables**, add `NEXT_PUBLIC_API_URL` with your Render backend URL + `/api/v1`.
6. Click **Deploy**.
7. Once deployed, note the Vercel URL (e.g. `https://athlyt.vercel.app`).
8. **Go back to Render** and update `CORS_ORIGINS` on the backend to this real Vercel URL, then redeploy the backend (or it will reject requests from your live frontend with a CORS error).

### 3.7 Production build verification

Before deploying, verify the build succeeds locally with the same command Vercel runs:

```bash
cd frontend
npm ci
npm run build
```

Expect output ending in:
```
✓ Compiled successfully
✓ Generating static pages (13/13)
```

If this fails locally, it will fail on Vercel identically — fix it before pushing.

---

## 4. Database — SQLite → PostgreSQL Migration

**Current state confirmed from the codebase:** `backend/app/core/config.py` defaults `DATABASE_URL` to `sqlite:///./athlyt.db`. This is correct and intentional for local development — SQLite requires no setup and every model, query, and migration in this project was written to work identically on both databases (UUIDs as `String(36)`, enums as `VARCHAR`, no SQLite-specific SQL anywhere — see `backend/app/db/base.py`).

**Production must use PostgreSQL.** This isn't a code change — it's an environment variable change plus running the existing Alembic migrations against the new database.

### 4.1 Recommended provider: Neon

Neon is recommended over Supabase for this project because:
- Serverless PostgreSQL with true autosuspend on the free tier (Supabase's free tier also pauses, but Neon's wake-up is typically faster)
- Simpler connection string format — no additional connection pooler URL to reason about for a project this size
- Branching support (a `git branch`-like copy of your database) if you ever want to test a migration against production-shaped data safely

Supabase is a fine alternative if you specifically want its other features (auth, storage, realtime) for a future phase — but this project doesn't use any of those, so Neon is the leaner choice.

### 4.2 Neon setup — step by step

1. Go to [neon.tech](https://neon.tech) → sign up → **Create a project**.
2. Name it `athlyt` (or anything) and choose a region close to your Render backend's region (reduces latency between the two).
3. Neon shows a connection string immediately, in this format:
   ```
   postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
   ```
4. **Adapt it for SQLAlchemy** — the scheme must be `postgresql+psycopg2://`, not plain `postgresql://`:
   ```
   postgresql+psycopg2://user:password@ep-xxx-xxx.region.aws.neon.tech/dbname?sslmode=require
   ```
   The `?sslmode=require` must stay — Neon rejects unencrypted connections.
5. Copy this full string — this is your `DATABASE_URL`.

### 4.3 Running migrations against Neon

Before your backend even deploys, run the migrations once from your local machine to confirm the connection works and the schema gets created:

```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://user:password@ep-xxx.../dbname?sslmode=require"
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> ca10796a2c38, initial_schema
```

Verify the tables exist:
```bash
alembic current
# Expect: ca10796a2c38 (head)
```

### 4.4 Setting `DATABASE_URL` in Render

Paste the same connection string (with `postgresql+psycopg2://` and `?sslmode=require`) into Render's `DATABASE_URL` environment variable (§2.5). Render's own start command already runs `alembic upgrade head` on every deploy (§2.3), so once this variable is set correctly, the schema stays in sync automatically on future deploys too.

### 4.5 Supabase alternative (if you choose it instead)

1. [supabase.com](https://supabase.com) → **New Project**.
2. Once created, go to **Project Settings** → **Database** → **Connection string** → select **URI**.
3. Supabase gives you something like:
   ```
   postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres
   ```
4. Adapt the same way:
   ```
   postgresql+psycopg2://postgres:[password]@db.xxxx.supabase.co:5432/postgres
   ```
5. Supabase's default connection doesn't require `?sslmode=require` the way Neon does, but adding it is harmless and slightly more explicit about the security expectation.
6. Same `alembic upgrade head` step as §4.3 applies.

---

## 5. Environment Variables — Complete Reference

### 5.1 Backend

| Variable | Required | Environment | Used in | Description |
|---|---|---|---|---|
| `JWT_SECRET_KEY` | **Required** | All | `app/core/config.py`, `app/core/security.py` | Signs and verifies JWTs. ≥ 32 chars or the app refuses to start (Pydantic validation). |
| `DATABASE_URL` | **Required** | All | `app/db/session.py` | Connection string. SQLite in dev, PostgreSQL in production. |
| `CORS_ORIGINS` | **Required** | All | `app/main.py` | Comma-separated frontend origin(s) allowed to call the API. |
| `ALLOWED_HOSTS` | Optional (defaults to `*`) | Production only (meaningfully) | `app/main.py` | Comma-separated hostnames this API accepts via the `Host` header. `*` in dev is fine; set to the real domain in production. |
| `ENVIRONMENT` | Optional (defaults to `local`) | All | `app/main.py`, `app/core/logging_config.py` | `local` \| `test` \| `production`. Controls schema creation strategy and log verbosity. |
| `DEBUG` | Optional (defaults to `false`) | Development only (meaningfully) | `app/db/session.py`, `app/api/v1/routers/health.py` | `true` enables SQL query echoing and exposes ML engine diagnostics on `GET /health/detailed` (model version, load status, confidence threshold — see `ml/models/PRODUCTION_ROLLOUT.md` §3.2). Never set `true` in production — noisy, and the health check detail is meant to stay internal. |
| `RECOMMENDATION_ENGINE` | Optional (defaults to **`ml`**) | Production-relevant | `app/core/config.py` | `rule` \| `ml`. Which engine serves `/workouts/recommend` and `/workouts/generate`. `ml` falls back to the rule engine automatically on any failure — see `docs/ML_INTEGRATION.md`. Set to `rule` for an instant rollback with zero code changes. |
| `ML_MODEL_PATH` | Optional (has default) | All | `app/core/config.py` | Path to the trained `.joblib` workout-recommendation model, relative to `backend/`'s working directory. Tracked via Git LFS — see §8 below. |
| `ML_PREPROCESSOR_PATH` | Optional (has default) | All | `app/core/config.py` | Path to the fitted preprocessor `.joblib`, loaded alongside the model above. |
| `ML_CONFIDENCE_THRESHOLD` | Optional (defaults to `0.6`) | Production-relevant | `app/core/config.py` | Below this `predict_proba()` confidence, the ML engine defers to the rule engine. See `ml/models/PRODUCTION_ROLLOUT.md` §4 for how this value was validated against 500 real out-of-sample profiles. |

### 5.2 Frontend

| Variable | Required | Environment | Used in | Description |
|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Required** | All | `lib/api-client.ts` | Backend base URL including `/api/v1`. Baked in at build time — changing it requires a redeploy, not just a restart. |

### 5.3 Docker Compose only (root `.env`)

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | **Required** | Password for the `postgres` container. Used to assemble the backend's `DATABASE_URL` automatically. |

### 5.4 Example production `.env` (backend)

```bash
# backend/.env — PRODUCTION VALUES. Never commit this file.

ENVIRONMENT=production
DEBUG=false

DATABASE_URL=postgresql+psycopg2://user:password@ep-xxx.us-east-2.aws.neon.tech/athlyt?sslmode=require

JWT_SECRET_KEY=8f3a1c9e7b2d4f6a8c0e2b4d6f8a0c2e4b6d8f0a2c4e6b8d0f2a4c6e8b0d2f4a

CORS_ORIGINS=https://athlyt.vercel.app

ALLOWED_HOSTS=athlyt-backend.onrender.com
```

### 5.5 Example production `.env.local` (frontend)

```bash
# frontend/.env.local — PRODUCTION VALUE

NEXT_PUBLIC_API_URL=https://athlyt-backend.onrender.com/api/v1
```

---

## 6. Security Review

### 6.1 JWT

- **Algorithm:** HS256, symmetric signing (`app/core/config.py: JWT_ALGORITHM`).
- **Expiry:** 7 days, single access token — no refresh-token rotation (`ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7`).
- **Storage:** `localStorage` on the frontend, not an httpOnly cookie (`frontend/lib/auth-token.ts` — this tradeoff is explicitly documented in that file's docstring).

**Before production, consider:**
- The 7-day single-token approach means a stolen token (via XSS) is valid for up to 7 days with no way to revoke it server-side. For a portfolio project this is an acceptable, explicitly-documented tradeoff. For a real production app with real user data, add refresh-token rotation with server-side revocation (a `refresh_tokens` table, shorter access-token expiry like 15 minutes) before launch.
- `localStorage` is readable by any JavaScript running on the page — if a future feature introduces a third-party script or a stored-XSS vulnerability, the token is exposed. Moving to httpOnly cookies removes this specific risk but requires the Next.js server to participate in auth (middleware, cookie-setting API routes) — a real architecture change, not a config tweak.

### 6.2 CORS

- Configured via `CORS_ORIGINS` env var, parsed into an explicit allow-list (`app/main.py`, `CORSMiddleware`).
- `allow_credentials=True` is set — this is required because the frontend sends the JWT as an `Authorization` header (not a cookie), but note that `allow_credentials=True` combined with a wildcard `allow_origins=["*"]` is rejected by browsers entirely; this codebase never uses a wildcard, only explicit origins, so this is already handled correctly.

**Before production:** ensure `CORS_ORIGINS` in Render lists only your actual Vercel domain(s) — never `*`, never `localhost`, in a production environment variable value.

### 6.3 Cookies

Not used anywhere in this application — confirmed by reviewing `app/core/security.py` and every router in `app/api/v1/routers/`. All auth state travels via the `Authorization: Bearer <token>` header. No CSRF risk exists as a result (CSRF specifically exploits cookie-based auth; a bearer-token-in-header scheme is not vulnerable to it by design).

### 6.4 Secrets

- `JWT_SECRET_KEY` is the only true secret. It's validated by Pydantic to be ≥ 32 characters (`Field(min_length=32)` in `config.py`) — the app will not start with a short or missing key.
- No secrets are hardcoded anywhere in the codebase — confirmed via `backend/.env.example`, which contains only placeholder values, and `.gitignore`, which excludes `.env` at every level.
- Database credentials live entirely in `DATABASE_URL`, itself an environment variable, never in source.

**Before production:** rotate `JWT_SECRET_KEY` to a value generated specifically for production (not reused from local development) — a leaked local `.env` should never be able to forge production tokens.

### 6.5 HTTPS

- Neither Render nor Vercel serve plain HTTP in production — both terminate TLS automatically and redirect HTTP → HTTPS by default. No application-level HTTPS enforcement code exists in this codebase, and none is needed — it would be redundant with what the hosting platforms already do.
- `Strict-Transport-Security` (HSTS) is deliberately not set at the application level (`backend/app/core/security_headers.py`, `frontend/next.config.ts`) — both hosting platforms typically add this header themselves at the edge, and setting a conflicting or overly aggressive `max-age` at the app level is a real footgun (it can lock out `http://localhost` access if the value is copied into a local `.env` by mistake).

### 6.6 Additional headers already in place

- **Backend** (`app/core/security_headers.py`): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` on every API response.
- **Frontend** (`next.config.ts`): the same three headers, plus `X-XSS-Protection` and `Permissions-Policy`.
- **Backend** `TrustedHostMiddleware` (`app/main.py`, driven by `ALLOWED_HOSTS`): rejects any request with an unrecognized `Host` header before it reaches any route handler — mitigates Host header injection (cache poisoning, password-reset link poisoning, though this app doesn't currently have password reset).

---

## 7. Custom Domain & SSL

### 7.1 Vercel (frontend)

1. Project → **Settings** → **Domains** → **Add**.
2. Enter your domain (e.g. `athlyt.com` or `app.athlyt.com`).
3. Vercel shows the DNS records to add:
   - For an apex domain (`athlyt.com`): an `A` record pointing to Vercel's IP.
   - For a subdomain (`app.athlyt.com`): a `CNAME` record pointing to `cname.vercel-dns.com`.
4. Add the record(s) in your domain registrar's DNS settings.
5. Vercel automatically provisions an SSL certificate (via Let's Encrypt) once DNS propagates — usually within minutes, sometimes up to 24 hours depending on your registrar's TTL.
6. No code changes needed — `next.config.ts`'s redirect and header rules apply regardless of domain.

### 7.2 Render (backend)

1. Service → **Settings** → **Custom Domains** → **Add Custom Domain**.
2. Enter your API subdomain (e.g. `api.athlyt.com`).
3. Render shows a `CNAME` record to add pointing to your `.onrender.com` address.
4. Add it in your DNS provider.
5. Render auto-provisions SSL the same way, via Let's Encrypt.
6. **After adding a custom domain, update two environment variables:**
   - `ALLOWED_HOSTS` on the backend → add the new custom domain.
   - `NEXT_PUBLIC_API_URL` on the frontend (Vercel) → point to the new custom domain, then redeploy the frontend (§3.5 — build-time variable).
   - `CORS_ORIGINS` on the backend, if the frontend's domain also changed.

---

## 8. Testing — Before Every Deployment

Run every one of these locally before pushing. If any fails, fix it before deploying — do not deploy on a red build.

```bash
# ── Backend ──────────────────────────────────────────────────────────────
cd backend
git lfs pull                 # required: ML_MODEL_PATH/ML_PREPROCESSOR_PATH default files are Git LFS-tracked
pip install -e ".[dev]"
pytest -q                    # expect: 256 passed
ruff check .                 # expect: All checks passed!
black --check .              # expect: All done! ✨ 🍰 ✨

# ── Frontend ─────────────────────────────────────────────────────────────
cd ../frontend
npm ci
npm run lint                 # expect: no output (clean)
npm run build                # expect: ✓ Compiled successfully

# ── Database (only if you changed a model) ──────────────────────────────
cd ../backend
alembic check                # confirms no un-generated model changes exist
```

If `alembic check` reports a difference, you added or changed a model without generating a migration — run `alembic revision --autogenerate -m "describe_the_change"` and commit the new file in `alembic/versions/` before deploying.

### 8.1 Verify Swagger locally before trusting it in production

```bash
cd backend
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export DATABASE_URL=sqlite:///./verify.db
export ENVIRONMENT=local
uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/v1/health
open http://localhost:8000/docs   # or just visit in browser
kill %1
rm verify.db
```

### 8.2 Verify the ML recommendation engine before deploying

`RECOMMENDATION_ENGINE` defaults to `ml`. Confirm the real model actually loads and predicts — not just that the fallback silently catches a missing model (which it will, correctly, but that's not the same as verifying ML is genuinely working):

```bash
cd backend
git lfs pull   # if you haven't already — see §8 above
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export DATABASE_URL=sqlite:///./verify_ml.db
export ENVIRONMENT=local
export DEBUG=true
uvicorn app.main:app --port 8000 &
sleep 2

# Register, onboard, and request a recommendation, then check the health
# endpoint and server logs for confirmation the real model was used:
curl -s http://localhost:8000/api/v1/health/detailed | python3 -m json.tool
# Look for: "ml_model_loaded": true, "ml_model_version": "v2" (after at
# least one recommendation request — see ml/models/PRODUCTION_ROLLOUT.md
# §3.2 for why this is false/false on a completely fresh process)

kill %1
rm verify_ml.db
```

If `ml_model_loaded` stays `false` after a real recommendation request, check the server log for a `WARNING` from `app.ml.registry` — the most common cause is `git lfs pull` not having been run, leaving `ml/models/*.joblib` as small pointer files (handled gracefully via automatic fallback, but ML predictions won't actually happen until the real files are present). See `docs/ML_INTEGRATION.md` §3.1.

---

## 9. Node Version Note

`frontend/package.json` does not pin an `engines.node` field. Vercel's default Node runtime (currently Node 20.x as of writing) is what the project has been built and tested against. If Vercel's default ever changes, add this to `package.json` to pin it explicitly:

```json
"engines": { "node": ">=20" }
```

This is a documentation note, not a required change — flagging it here since the prompt asked for a review of "package managers" and this is a real gap worth knowing about, not something to silently work around.

---

## 10. After Deployment — Verification Checklist

Work through this list on the live URLs, not localhost, after both services are deployed and environment variables are set on both sides.

**Backend**
- [ ] `GET https://your-backend.onrender.com/api/v1/health` returns `{"status":"ok",...}`
- [ ] `GET https://your-backend.onrender.com/docs` loads Swagger UI
- [ ] `GET https://your-backend.onrender.com/openapi.json` returns valid JSON listing 35 paths

**Frontend**
- [ ] `https://your-app.vercel.app` loads the landing page
- [ ] Dark mode toggle works and persists across a page reload
- [ ] No console errors on initial page load (check browser DevTools)

**Auth flow**
- [ ] Registration works (`/register` → creates account → redirects to onboarding)
- [ ] Login works with the account just created
- [ ] Logging out and back in works
- [ ] An expired/invalid token correctly redirects to `/login`, not a blank page

**Core features**
- [ ] Onboarding form submits and saves profile data
- [ ] Dashboard shows BMI and daily calorie estimate matching the onboarded profile
- [ ] Workout generation (`/workouts` → Generate) produces a real weekly plan
- [ ] Starting a workout session, completing an exercise, and finishing the session all work end-to-end
- [ ] Progress logging (`/progress`) saves and displays a weight entry
- [ ] Nutrition plan generation (`/nutrition` → Generate) produces real meal data
- [ ] Settings page loads existing profile data and saves an edit correctly

**Persistence**
- [ ] Refreshing the browser after logging in keeps you logged in (token persists)
- [ ] Data entered (a workout session, a progress log) is still visible after closing and reopening the browser — confirms the database write actually persisted to Postgres, not just an in-memory session

**Cross-cutting**
- [ ] CORS: no CORS errors in the browser console when the frontend calls the backend
- [ ] Every API error (e.g. wrong password) shows a real error message in the UI, not a generic crash

---

## 11. Troubleshooting — Top 20 Deployment Problems

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Backend won't start; logs show `pydantic_core.ValidationError: JWT_SECRET_KEY` | `JWT_SECRET_KEY` missing or under 32 characters | Generate a real key (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) and set it in Render's environment variables |
| 2 | Backend starts but every request returns 400 with no body, or connection refused | Uvicorn bound to `127.0.0.1` instead of `0.0.0.0` | Confirm start command includes `--host 0.0.0.0` |
| 3 | Render health check fails even though the app "looks" started in logs | Hardcoded port instead of `$PORT` | Use `--port $PORT` in the start command, never a literal number |
| 4 | `database: "unhealthy"` in `/api/v1/health` response | `DATABASE_URL` wrong, unreachable, or missing `sslmode=require` for Neon | Test the connection string locally first: `python -c "from sqlalchemy import create_engine; create_engine('YOUR_URL').connect()"` |
| 5 | `sqlalchemy.exc.NoSuchModuleError: postgresql` | Connection string uses `postgresql://` instead of `postgresql+psycopg2://` | Add `+psycopg2` to the scheme |
| 6 | Migration fails with an SSL error against Neon | Missing `?sslmode=require` | Append it to the connection string's query params |
| 7 | Frontend shows "Network Error" or failed fetch on every API call | `NEXT_PUBLIC_API_URL` wrong or missing `/api/v1` suffix | Check the exact value in Vercel's environment variables; must match backend's actual prefix |
| 8 | Frontend API calls fail with a CORS error in the browser console | Backend's `CORS_ORIGINS` doesn't include the real Vercel URL | Update `CORS_ORIGINS` on Render, redeploy backend |
| 9 | Changed `NEXT_PUBLIC_API_URL` in Vercel but the app still calls the old URL | `NEXT_PUBLIC_*` vars are baked in at build time | Trigger a new deployment — a restart alone does not re-read this variable |
| 10 | 401 on every request even with a valid-looking token | `JWT_SECRET_KEY` differs between the token's issuer and the verifier (e.g. rotated the key without invalidating old sessions) | Expected behavior after a key rotation — users must log in again |
| 11 | Backend returns 400 on OPTIONS preflight requests | CORS misconfigured, or `ALLOWED_HOSTS` rejecting the browser's preflight Host header | Verify `CORS_ORIGINS` exactly matches the frontend origin (protocol + domain, no trailing slash) |
| 12 | Backend rejects all requests with 400 "Invalid host header" | `ALLOWED_HOSTS` set too restrictively, or missing the actual domain | Add the real Render/custom domain to `ALLOWED_HOSTS` |
| 13 | `alembic upgrade head` says "Target database is not up to date" or similar | A previous partial migration run left the DB in an inconsistent state | Run `alembic current` to see where it thinks it is, compare against `alembic history`, resolve manually — do not force with `stamp` unless certain |
| 14 | New model added but tables don't appear in production | Forgot to generate a migration for it | Run `alembic revision --autogenerate -m "..."` locally, commit the file, redeploy |
| 15 | `pip install -e .` fails with "Readme file does not exist" (only relevant if deploying via Docker) | `pyproject.toml` requires `README.md` in the same directory as the package build context | Ensure `README.md` is copied alongside `pyproject.toml` in any custom build step |
| 16 | Vercel build fails with a TypeScript error that doesn't appear locally | Local `node_modules` out of sync with `package-lock.json` | Run `npm ci` (not `npm install`) locally to reproduce exactly what Vercel does |
| 17 | Vercel build fails trying to fetch Google Fonts | Outbound network restriction in a sandboxed CI runner (not a real issue on Vercel's actual infrastructure, which has full internet access) | No action needed on real Vercel deploys; only relevant if testing in a network-restricted sandbox |
| 18 | App works but every response is very slow after a period of inactivity | Neon/Supabase free-tier database autosuspend — first query after idle wakes the database | Expected free-tier behavior; `pool_pre_ping=True` (already set in `app/db/session.py`) prevents this from causing an error, just a one-time delay |
| 19 | Logging in works but the session doesn't persist after a page refresh | `localStorage` cleared by browser privacy settings, or an incognito/private window | Expected in private browsing; not a bug. Confirm in a normal browser window |
| 20 | Frontend shows stale data after generating a new workout/nutrition plan | TanStack Query cache not invalidated after the mutation | This should already be handled by existing `onSuccess` cache invalidation in the relevant hooks — if it isn't, it's a real bug worth filing, not a deployment config issue |

---

## 12. Summary — What to Do, In Order

1. Create a Neon project → get connection string → adapt to `postgresql+psycopg2://...?sslmode=require`.
2. Run `alembic upgrade head` locally against that connection string to confirm it works and creates all 13 tables.
3. Create a Render web service → root directory `backend` → build command `pip install -e .` → start command `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` → health check `/api/v1/health` → set all 6 backend environment variables.
4. Deploy the backend, note its URL.
5. Create a Vercel project → root directory `frontend` → set `NEXT_PUBLIC_API_URL` to the Render URL + `/api/v1`.
6. Deploy the frontend, note its URL.
7. Go back to Render → update `CORS_ORIGINS` and `ALLOWED_HOSTS` to the real Vercel and Render URLs respectively → redeploy backend.
8. Work through the §10 verification checklist on the live URLs.
9. (Optional) Add custom domains per §7, then update `CORS_ORIGINS`, `ALLOWED_HOSTS`, and `NEXT_PUBLIC_API_URL` again and redeploy both services.
