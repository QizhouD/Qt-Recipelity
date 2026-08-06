# Recipelity — Intelligent Recipe Management

Recipelity is a web application built with Vue 3 and FastAPI for managing recipes, uploading food images, estimating nutrition, and creating recipe content with generative AI. The original PyQt desktop application remains in the repository, but active development now takes place in `frontend/` and `backend/`.

## Features

- Create, edit, delete, paginate, search, and filter recipes
- Manage ingredients, quantities, cooking steps, tags, and cuisines
- Upload JPEG, PNG, and WebP images
- Correct image orientation, resize large images, and convert uploads to WebP
- Display responsive recipe images with lazy loading and error fallbacks
- Estimate nutrition from ingredient names, quantities, and units
- Support common Chinese and English ingredient names
- Convert grams, kilograms, milliliters, liters, pieces, tablespoons, and teaspoons
- Report ingredients that could not be matched during nutrition analysis
- Generate an editable recipe and nutrition draft from a food image
- Generate a recipe cover image from recipe text

> AI-generated content and nutrition values are estimates. Review all results before saving or using them. They are not medical or professional dietary advice.

## Technology Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Element Plus, and ECharts
- Backend: Python 3.11+, FastAPI, Pydantic, and SQLAlchemy 2 (async)
- Database: MySQL 8.4 (Docker / production); SQLite for local dev, tests, and legacy data migration
- Migrations: Alembic (``alembic upgrade head`` creates the schema; ``scripts/migrate_db.py`` imports legacy data)
- AI: OpenAI Responses API and GPT Image
- Quality: pytest, Ruff, Vitest, and TypeScript checks
- Deployment: Docker Compose and Nginx

## Project Structure

```text
backend/                 FastAPI routes, models, services, and tests
frontend/                Vue 3 frontend
deploy/                  Backend/frontend Dockerfiles and Nginx configuration
scripts/                 Database audit and migration utilities
data/                    Runtime database and generated media
core/, ui/, main*.py     Preserved legacy PyQt application
```

## Local Development

### Backend

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend services:

- OpenAPI documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health/live>

### Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173/index.html>. The Vite development server proxies `/api` and `/media` requests to the backend.

## AI Configuration

Copy `.env.example` to `backend/.env`:

```powershell
Copy-Item .env.example backend\.env
```

Configure the server-side API credentials:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key
AI_VISION_MODEL=gpt-5.6-luna
AI_IMAGE_MODEL=gpt-image-2
AI_REQUEST_TIMEOUT=90
```

Keep API keys in local environment variables or deployment-platform secrets. Never commit them to Git. Recipe management, image uploads, and nutrition analysis remain available without an API key; AI endpoints return an explicit configuration error.

## Frontend Pages

| Route | Page | Description |
|---|---|---|
| `/` | Redirect | Automatically redirects to `/recipes` |
| `/recipes` | Recipe list | Search, filtering, pagination, and URL-synchronized filters |
| `/recipes/new` | Create recipe | Reorder ingredients and steps, upload images, and validate input |
| `/recipes/:id` | Recipe details | Nutrition results, ingredient matching, and not-found handling |
| `/recipes/:id/edit` | Edit recipe | Unsaved-change detection and navigation confirmation |
| `/ai-studio` | AI Studio | Image-to-recipe and recipe-to-image workflows with configuration guidance |
| `/about` | About | Project overview and nutrition/AI usage disclaimers |
| `/:pathMatch(.*)*` | Not found | 404 page with a link back to the recipe list |

## Main API Endpoints

```text
GET    /api/v1/recipes
POST   /api/v1/recipes
GET    /api/v1/recipes/{id}
PATCH  /api/v1/recipes/{id}
DELETE /api/v1/recipes/{id}
POST   /api/v1/recipes/{id}/nutrition:calculate
POST   /api/v1/media/images
POST   /api/v1/ai/recipe-from-image
POST   /api/v1/ai/image-from-recipe
GET    /health/live
GET    /health/ready
```

Every HTTP response includes an `X-Request-ID` header. Clients may provide a safe
request ID using the same header; otherwise the server generates one. Access logs
are emitted as JSON and intentionally exclude request bodies, headers, query strings,
database URLs, and API keys.

URL-based recipe importing has been removed from the active product flow and registered API.

## Testing and Validation

Run backend checks:

```powershell
cd backend
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest tests -q
```

Run frontend checks:

```powershell
cd frontend
npm run lint              # ESLint + vue-tsc
npm run test:unit         # Vitest unit tests
npm run test:e2e          # Playwright E2E tests (headless)
npm run test:e2e:headed   # Playwright E2E tests (headed browser)
npm run build             # Production build
```

## Docker

Build and start the full stack (MySQL + Backend + Frontend):

```powershell
Copy-Item .env.example .env
# Edit .env to set MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, and OPENAI_API_KEY
docker compose up --build
```

The default web entry point is <http://localhost:8080>. The backend runs Alembic migrations automatically on startup (``alembic upgrade head``). Persistent data is stored in named volumes:

MySQL is exposed to local database tools on port `3307` by default. Connect with host
`localhost`, port `3307`, database/user `recipelity`, and the password configured by
`MYSQL_PASSWORD`. Containers continue to connect internally through `mysql:3306`.

| Volume | Contents |
|---|---|
| `mysql_data` | MySQL 8.4 database files |
| `recipe_data` | Application data (generated media) |
| `media_data` | Uploaded recipe images (survives container rebuild) |

### Smoke Test

After starting the stack, run the smoke test:

```powershell
bash scripts/smoke_test.sh
```

Or manually verify:
- <http://localhost:8000/health/live> — backend liveness
- <http://localhost:8000/health/ready> — backend readiness (DB connected)
- <http://localhost:8080/> — frontend homepage
- <http://localhost:8080/recipes/1> — SPA deep link (should not 404)
- <http://localhost:8080/api/v1/recipes?page=1> — API via nginx proxy

Configure ``.env`` with real secrets before production deployment. See ``.env.example`` for reference.

### Media Uploads

Uploaded images are saved to the directory configured by ``MEDIA_ROOT`` (default: ``data/uploads``) and served under ``/media/``. In Docker, this directory is backed by the ``media_data`` named volume — images persist across container recreations.

Supported formats: JPEG, PNG, WebP. Max file size: 5 MB (configurable via ``IMAGE_MAX_BYTES``).

## Database Migration

### Fresh Setup (Recommended Path A)

1. Start MySQL (Docker or external) and create the empty database.
2. Run Alembic to create the schema:
   ```bash
   cd backend
   DATABASE_URL=mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4 \
     alembic upgrade head
   ```
3. Import legacy SQLite data (idempotent — safe to re-run):
   ```bash
   python scripts/migrate_db.py data/recipes.db \
     --target mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4
   ```

### Existing Verified Database (Path B)

Only use ``alembic stamp head`` on a database whose schema you have verified matches the Alembic head revision exactly. This marks the revision as applied without running migrations:

```bash
DATABASE_URL=mysql+asyncmy://... alembic stamp head
```

### Local Development (SQLite)

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./data/recipes.db alembic upgrade head
```

> **⚠️ Always back up your original SQLite file before running any migration.** Do not run ``alembic upgrade head`` directly on an existing ``data/recipes.db`` — if tables already exist, Alembic will fail with "table already exists". Use the two-step path: create a fresh target DB with Alembic, then import data with ``migrate_db.py``.

## Additional Documentation

- [Refactoring plan](REFACTOR_PLAN.md)
- [Next-phase plan](NEXT_PHASE_PLAN.md)

## License

MIT
