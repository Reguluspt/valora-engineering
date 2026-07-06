.PHONY: up down backend-dev frontend-dev worker-dev backend-test worker-test

up:
	docker compose up -d

down:
	docker compose down

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm install && npm run dev

worker-dev:
	cd worker && python -m worker.main

backend-test:
	cd backend && pytest

worker-test:
	cd worker && pytest
