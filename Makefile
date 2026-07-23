.PHONY: install db migrate dev serving control traffic frontend lint typecheck seed-weights

install:
	uv sync
	cd frontend && npm install

db:
	docker compose up -d db

migrate:
	uv run alembic upgrade head

seed-weights:
	uv run python scripts/seed_weights.py

# Control plane API (:8000) + serving app (:8001). Run in two shells, or use `make control` / `make serving`.
dev: control

control:
	uv run uvicorn backend.app.main:app --reload --port 8000

serving:
	uv run uvicorn serving.app.main:app --reload --port 8001

frontend:
	cd frontend && npm run dev

lint:
	uv run ruff check .

typecheck:
	uv run mypy backend serving mcp_servers
