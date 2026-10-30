# Repository Guidelines

## Project Structure & Module Organization

`backend/app/api/` contains FastAPI routes; `entities/` holds SQLAlchemy models, `schemas/` request and result models, `services/` business logic, `configuration/` file settings, `storage/` file storage, `agents/` AI workflows, `prompts/` instructions, and `clients/` model and HiFlow integrations. Tests live in `backend/tests/`; the Vue 3 UI lives in `frontend/src/`. `.env.example` lists configuration.

## Build, Test, and Development Commands

- Copy `.env.example` to `.env` if absent, then run `cd backend; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000`. Set writable storage in the file's `DATA_DIR` if needed.
- `cd frontend; npm install; npm run dev`: run Vite at `http://localhost:5173`, with `/api` proxied to port 8000.
- `cd frontend; npm run build`: type-check with `vue-tsc` and produce `dist/`.
- `python scripts/smoke-test.py`: check basic endpoints after the local backend starts.

## Coding Style & Naming Conventions

Use four-space indentation and `snake_case` for Python functions and modules. In the frontend, follow nearby Vue/TypeScript formatting, use `camelCase` variables, and name components and types in PascalCase. Keep API contracts in `backend/app/schemas/`, database writes and stage transitions in `services/recruitment.py`, and external calls in `clients/`. No repository-wide formatter or linter is configured; keep changes focused and run the frontend type-check.

## Testing Guidelines

Run `cd backend; python -m pytest -q`. Pytest discovers `test_*.py` files and `test_*` functions. Add state-machine cases to `test_core.py`, HTTP flows to `test_api.py`, AI modes to `test_ai_modes.py`, client cases to `test_clients.py`, and configuration cases to `test_configuration.py`. Tests use a temporary configuration file and database through `conftest.py`. No coverage threshold is configured.

Do not use Playwright workflows in this repository, per the owner's preference.

## Commit & Pull Request Guidelines

This checkout has no Git history, so no existing commit-message convention can be verified. Use short, imperative subjects that name the change, such as `Add review validation for interview dates`. In pull requests, summarize behavior, list commands run, link the relevant issue when one exists, and include screenshots for UI changes.

## Security & Configuration

Copy `.env.example` to `.env`; never commit API keys or webhook URLs. Browser-supplied model keys must remain request-scoped and out of database and LangGraph state. Use fictional or anonymized resumes. This MVP has no authentication or production-grade file protections, so do not expose it publicly or use it with unauthorized candidate data.
