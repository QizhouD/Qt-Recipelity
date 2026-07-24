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
- Backend: Python 3.11+, FastAPI, Pydantic, and SQLAlchemy 2
- Database: SQLite for current local development; see `NEXT_PHASE_PLAN.md` for the planned MySQL migration
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
```

URL-based recipe importing has been removed from the active product flow and registered API.

## Testing and Validation

Run backend checks:

```powershell
cd backend
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest tests -q
```

Build the frontend:

```powershell
cd frontend
npm run build
```

Backend tests cover recipe CRUD, search and filtering, nutrition calculation, image uploads, AI request validation, and safe behavior when AI credentials are unavailable.

## Docker

Build and start the application:

```powershell
docker compose up --build
```

The default web entry point is <http://localhost:8080>. SQLite data and generated media are stored in a named volume. Before production deployment, configure MySQL, HTTPS, backups, monitoring, and `OPENAI_API_KEY`.

## Additional Documentation

- [Refactoring plan](REFACTOR_PLAN.md)
- [Next-phase plan](NEXT_PHASE_PLAN.md)

## License

MIT
