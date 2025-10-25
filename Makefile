.PHONY: help install dev build up down logs clean test format

help:
	@echo "AARIS - Academic Journal Reviewer"
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Run development servers"
	@echo "  build      - Build Docker images"
	@echo "  up         - Start Docker services"
	@echo "  down       - Stop Docker services"
	@echo "  logs       - View Docker logs"
	@echo "  clean      - Clean Docker resources"
	@echo "  test       - Run tests
  format     - Format code with black"

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev:
	@echo "Starting development servers..."
	python run.py &
	cd frontend && npm start

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f

test:
	pytest tests/

format:
	autoflake --remove-unused-variables --remove-all-unused-imports -ri .
	isort .
	black .
	cd frontend && npm run format 2>/dev/null || echo "No frontend formatter configured"