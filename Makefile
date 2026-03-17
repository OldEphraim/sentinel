.PHONY: up down build logs seed clean

up:
	docker compose up

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

seed:
	uv run --with httpx python scripts/seed.py

clean:
	docker compose down -v
	docker system prune -f
