.PHONY: install db migrate dev serving control traffic frontend lint typecheck seed-weights seed-db seed

install:
	uv sync
	cd frontend && npm install

db:
	docker compose up -d db

migrate:
	uv run alembic upgrade head

seed-weights:
	uv run python scripts/seed_weights.py

seed-db:
	uv run python scripts/seed_db.py

# Full seed: CNN checkpoints, then the deploy + reference-profile rows.
seed: seed-weights seed-db

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
