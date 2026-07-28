# Athlyt — Project Bible

The definitive reference for conventions, patterns, and decisions. Read before contributing or extending.

---

## The three rules

1. **Routers are thin.** Parse the request, call one service method, return a schema. No business logic, no SQL, no if/else.
2. **Services own all logic.** The only place business rules live. Services call repositories — never each other's repositories, never ORM models directly.
3. **Repositories are the only DB layer.** The only files that `import Session`. Every query lives here, named after what it returns, not how it's implemented.

Breaking any of these makes the codebase harder to test and refactor. If you feel the urge to put a query in a router, write a repository method. If you feel the urge to put business logic in a repository, write a service.

---

## Backend patterns

### Adding a new feature (backend)

1. **Model** — add to `app/models/`. Inherit `UUIDPrimaryKeyMixin, TimestampMixin, Base`. Add to `app/models/__init__.py`.
2. **Schema** — add Pydantic schemas to `app/schemas/`. One file per domain. Always `ConfigDict(from_attributes=True)` on response models.
3. **Repository** — add to `app/repositories/`. Module-level functions, `db: Session` as first param. No business logic.
4. **Service** — add to `app/services/`. Class with stateless methods. Calls repositories, raises domain exceptions, never raises `HTTPException`.
5. **Router** — add to `app/api/v1/routers/`. Register in `app/api/v1/router.py`. Inject `CurrentUser` and `DbSession`.
6. **Tests** — integration tests in `tests/test_<feature>_api.py`, unit tests in `tests/test_<feature>_service.py`.

### Exception hierarchy

```python
AppException(Exception)          # base
├── NotFoundError    → 404
├── ValidationError  → 422
├── ConflictError    → 409
└── UnauthorizedError → 401
```

Services raise these. The global handler in `core/exception_handlers.py` converts them to `{"detail": "..."}`. Routers never catch domain exceptions.

### Enum convention

Enums live in `app/models/enums.py`. Used in both ORM columns (`Enum(MyEnum, native_enum=False)`) and Pydantic schemas. `native_enum=False` prevents Postgres ALTER TYPE pain.

### UUID convention

`String(36)` everywhere. Application-generated (UUID4 via `uuid.uuid4()`), not database-generated. Works identically on SQLite and PostgreSQL.

---

## Frontend patterns

### Adding a new page

1. Create `app/(app)/<route>/page.tsx` — data orchestration + layout.
2. Create `app/(app)/<route>/loading.tsx` — skeleton placeholder.
3. Add data fetching to `hooks/use-dashboard-data.ts` (or a new hook file if domain is large).
4. Add TypeScript types to `types/user.ts`.
5. Add the route to `components/shared/sidebar.tsx`.

### Hook conventions

- All TanStack Query hooks live in `hooks/`.
- Never define `useQuery`/`useMutation` inside a page component — extract to a hook.
- Query keys follow `["domain", "sub-resource", ...params]` — e.g. `["progress", "logs", 90]`.
- Mutations include `onSuccess` invalidation of affected query keys.

### Component conventions

- **Shared** (`components/shared/`) — not domain-specific, reusable across pages.
- **Domain** (`components/workouts/`, `components/nutrition/` if added) — specific to one feature.
- **UI** (`components/ui/`) — shadcn/ui primitives; don't modify these.
- Props interfaces are always explicit — no inline prop types for reusable components.

### Animation conventions

All animation variants use the same easing: `ease: [0.16, 1, 0.3, 1]` (custom spring-like cubic bezier). Duration 0.3–0.4s for content transitions, 0.15s for hover transitions. Stagger children at 0.06–0.08s intervals.

Always wrap stagger-animated children in `Variants` typed constants. Never use `any` for animation props.

`prefers-reduced-motion` is respected by `AmbientBackground` (orbs and cursor glow disabled) and all CSS animations have a `@media (prefers-reduced-motion: reduce)` guard.

### Type safety

- No `any` in committed code — use `unknown` + type narrowing, or proper interfaces in `types/user.ts`.
- `eslint-disable @typescript-eslint/no-explicit-any` is banned in pages.
- If you need to type an API response, add the interface to `types/user.ts` and use it in the hook.

---

## Testing conventions

### Backend

- **Integration tests** — `tests/test_<feature>_api.py`. Use the `client` fixture (TestClient + lifespan). Each test registers a new user via `factories.py` unique email. Tests are isolation-aware: shared in-memory DB across the suite.
- **Unit tests** — `tests/test_<feature>_service.py`. Use the `db` fixture directly. Call `seed_exercises(db)` explicitly if the test needs exercises (don't rely on test order).
- All new features require both integration and unit tests before merge.

### Frontend

- The build (`npm run build`) is the TypeScript type-check gate.
- ESLint runs on `npm run lint`.
- No Vitest or Playwright yet (Milestone 11 in the original roadmap).

---

## Git conventions

- `main` — always deployable.
- Conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Never commit `.env` or `athlyt.db`. Both are in `.gitignore`.
- After every milestone: `git add -A && git commit -m "feat: ..." && git push origin main`.

---

## What's deliberately out of scope

These were consciously not built, not forgotten:

| Feature | Reason |
|---|---|
| Refresh token rotation | Single 7-day token is the right tradeoff for a portfolio project |
| Async SQLAlchemy | No performance benefit at this scale; adds setup complexity |
| mypy | ruff catches real bugs; mypy config overhead not worth it for solo project |
| PostgreSQL in dev | SQLite is identical for this codebase; simpler local setup — production uses Postgres via `DATABASE_URL` |
| Email verification | Real infrastructure (SMTP, token storage, resend logic); deferred |
| Progress photos | Requires object storage (S3/R2) and multipart upload; deferred |
| AI coach | Needs LLM API key and conversation management; deferred |
| Real ML inference | Model trained in Colab; inference endpoint wired but no artifact yet |

**Now implemented (previously listed here as deferred):** Alembic migrations, Docker (backend/frontend/compose stack), CI/CD (GitHub Actions), production deployment (Vercel + Render + Neon). See `CHANGELOG.md` for when each landed.
