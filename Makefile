.PHONY: install api web test lint check up down

install:  ## needs uv (https://docs.astral.sh/uv/) and Node 22
	cd backend && uv sync --extra dev
	cd frontend && npm install

api:  ## run the API with auto-reload on :8000
	cd backend && uv run alembic upgrade head && uv run uvicorn app.main:app --reload

web:  ## run the frontend dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run typecheck && npm run lint

check: lint test

up:
	docker compose up --build -d

down:
	docker compose down
