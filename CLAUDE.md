# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Recipelity is being refactored from a PyQt6 desktop app to a **Vue 3 + FastAPI** web application.
The legacy PyQt code (`main.py`, `core/`, `ui/`) is preserved but frozen — all new development
happens in `backend/` and `frontend/`.

**Database**: MySQL 8.4 is the Docker/production target. SQLite is used for **tests**,
**local development**, and as the **legacy data source** for `migrate_db.py`.
Alembic manages all schema creation. URL-based recipe importing has been removed.

## Commands

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # dev server
python -m pytest tests/ -v                     # run tests
python -m ruff check app/                      # lint
python -m ruff check app/ --fix                # auto-fix lint

# Database migrations (Alembic — creates schema, does NOT import data)
DATABASE_URL=mysql+asyncmy://... alembic upgrade head    # apply all migrations
DATABASE_URL=mysql+asyncmy://... alembic downgrade -1    # roll back one migration
python -m alembic revision --autogenerate -m "description"  # create new migration

# Scripts (run from repo root)
python scripts/audit_db.py [path-to-db]        # read-only DB audit
python scripts/migrate_db.py SOURCE.db --target DATABASE_URL          # idempotent migration
python scripts/migrate_db.py SOURCE.db --target DATABASE_URL --dry-run  # preview only
```

### Frontend (Vue 3 + TypeScript)

```bash
cd frontend
npm install
npm run dev              # dev server on :5173, proxies /api to :8000
npm run build            # production build to dist/
npm run lint             # ESLint
```

### Docker

```bash
docker compose up -d     # full stack: frontend (:80), backend (:8000)
docker compose config    # validate compose file
```

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan, CORS, router registration
│   ├── api/                 # REST routers
│   │   ├── recipes.py       # GET/POST /api/v1/recipes, GET/PATCH/DELETE /api/v1/recipes/{id}
│   │   ├── ai.py            # POST /api/v1/ai/recipe-from-image, /api/v1/ai/image-from-recipe
│   │   └── media.py         # POST /api/v1/media/images (upload)
│   ├── core/config.py       # Pydantic Settings (env-driven, see .env.example)
│   ├── db/session.py        # AsyncSession factory + FastAPI dependency (get_db)
│   ├── models/recipe.py     # SQLAlchemy 2.0 ORM (unified, no language variants)
│   ├── schemas/recipe.py    # Pydantic v2 domain contracts (all I/O validated here)
│   ├── services/
│   │   ├── recipe_service.py    # Business logic: CRUD, search
│   │   └── nutrition_service.py # Ingredient-based nutrition estimation
│   └── providers/ai_recipe_provider.py # OpenAI provider for image↔recipe AI
├── alembic/                 # Alembic migrations (env.py, versions/)
├── alembic.ini              # Alembic config (sqlalchemy.url from env)
└── tests/
    ├── conftest.py          # Shared fixtures (in-memory SQLite)
    ├── test_health.py       # Smoke tests
    ├── test_recipes.py      # CRUD + search + nutrition integration tests
    └── test_migrations.py   # Alembic upgrade/downgrade verification

frontend/
├── src/
│   ├── main.ts              # Vue 3 + Pinia + Element Plus bootstrap
│   ├── App.vue              # Root — renders AppLayout
│   ├── api/client.ts        # Axios instance, /api/v1 base URL
│   ├── router/index.ts      # Vue Router: /, /recipes/:id, /recipes/new, /recipes/:id/edit, /ai-studio
│   ├── stores/recipe.ts     # Pinia store: recipe CRUD, filters, pagination
│   ├── types/index.ts       # TS interfaces matching OpenAPI schemas
│   ├── layouts/AppLayout.vue # Responsive header + sidebar + <router-view>
│   ├── views/
│   │   ├── RecipeList.vue   # Grid of RecipeCards + pagination
│   │   ├── RecipeDetail.vue # Full recipe view + nutrition chart + delete
│   │   ├── RecipeForm.vue   # Create / edit form with structured ingredient/step editors
│   │   └── AIStudio.vue     # AI: image→recipe + recipe→image generation
│   └── components/
│       ├── RecipeCard.vue    # Card with image, name, tags, time
│       ├── RecipeImage.vue   # Image display with fallback
│       ├── FilterPanel.vue   # Keyword, cuisine, tags, difficulty, time filters
│       └── NutritionChart.vue # ECharts pie chart
└── index.html

scripts/
├── audit_db.py      # Read-only audit of legacy SQLite DB
└── migrate_db.py    # SQLite → MySQL: idempotent, dedup by name+source_url, pre/post counts

deploy/
├── Dockerfile.backend
├── Dockerfile.frontend
└── nginx/nginx.conf  # Serves SPA + proxies /api and /health to backend
```

### Data Models

- **Recipe** — name, description, prep_time/cook_time, difficulty (1-5), cuisine, image_url, source_url, created_at, updated_at
- **Ingredient** — name, amount (float), unit, FK → Recipe (ON DELETE CASCADE)
- **Step** — order (int), description, FK → Recipe
- **Nutrition** — one-to-one with Recipe; calories/protein/fat/carbs/fiber/sugar/sodium + `source` and `calculated_at` audit fields
- **Tag** — M2M with Recipe via `recipe_tag` table

`Recipe.total_time` is a **SQL hybrid property** — safe for both Python access and SQL WHERE filtering.

### Key Design Decisions

- **Request-scoped DB sessions** via FastAPI `Depends(get_db)` — no global session.
- **ORM never leaks to API** — all responses use Pydantic `model_validate()` with `from_attributes=True`.
- **Eager loading on write** — `create_recipe` and `update_recipe` re-select with `selectinload()` so Pydantic can traverse relationships outside the session.
- **Async SQLAlchemy** throughout — `AsyncSession`, `asyncmy` for MySQL 8.4 (production), `aiosqlite` for local dev and tests.
- **Alembic for schema migrations** — production uses `alembic upgrade head`; `Base.metadata.create_all()` only when `AUTO_CREATE_TABLES=true` (local dev).
- **Docker Compose** full stack — MySQL 8.4 + Backend (FastAPI) + Frontend (Nginx), with health checks and named volumes.
- **Idempotent data migration** — `scripts/migrate_db.py` deduplicates by (name, source_url), safe to re-run.
- **AI provider interface** — pluggable; returns a degradation notice when unconfigured, never random data.
- **Nutrition `source` field** tracks whether data is `manual` or `calculated`, with `calculated_at` timestamp.
