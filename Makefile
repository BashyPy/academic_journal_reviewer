.PHONY: help install dev prod test clean lint format security docker-dev docker-prod docker-stop docker-clean backup restore logs health ssl

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f docker-compose.yml
DOCKER_COMPOSE_PROD := $(DOCKER_COMPOSE) -f docker-compose.prod.yml
DOCKER_COMPOSE_TEST := $(DOCKER_COMPOSE) -f docker-compose.test.yml

help: ## Show this help message
	@echo "AARIS - Academic Agentic Review Intelligence System"
	@echo "===================================================="
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Development Setup
# ============================================================================

install: ## Install Python dependencies
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "✓ Dependencies installed"

install-dev: install ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements-test.txt
	@echo "✓ Development dependencies installed"

venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv .venv
	@echo "✓ Virtual environment created"
	@echo "Activate with: source .venv/bin/activate"

setup: venv install ## Complete development setup
	@echo "✓ Development environment ready"

# ============================================================================
# Running Services
# ============================================================================

dev: ## Run development server
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend development server
	@echo "Starting frontend development server..."
	cd frontend && npm install && npm start

dev-all: ## Run both backend and frontend
	@echo "Starting all services..."
	./scripts/start_all.sh

stop: ## Stop all running services
	@echo "Stopping services..."
	./scripts/stop_all.sh

status: ## Check service status
	@echo "Checking service status..."
	./scripts/status.sh

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "Running tests..."
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	$(PYTEST) tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	$(PYTEST) tests/integration/ -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	$(PYTEST) tests/ -v --looponfail

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linters (pylint, flake8)
	@echo "Running linters..."
	pylint app/
	flake8 app/

format: ## Format code with black and isort
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/
	@echo "✓ Code formatted"

format-check: ## Check code formatting
	@echo "Checking code formatting..."
	black --check app/ tests/
	isort --check-only app/ tests/

type-check: ## Run type checking with mypy
	@echo "Running type checks..."
	mypy app/

security: ## Run security checks
	@echo "Running security checks..."
	bandit -r app/ -ll
	safety check

quality: lint format-check type-check security ## Run all quality checks

# ============================================================================
# Docker - Development
# ============================================================================

docker-dev: ## Start development environment with Docker
	@echo "Starting development environment..."
	cd deployment && $(DOCKER_COMPOSE_DEV) up -d
	@echo "✓ Development environment started"

docker-dev-build: ## Build and start development environment
	@echo "Building development environment..."
	cd deployment && $(DOCKER_COMPOSE_DEV) up -d --build
	@echo "✓ Development environment built and started"

docker-dev-logs: ## View development logs
	cd deployment && $(DOCKER_COMPOSE_DEV) logs -f

docker-dev-stop: ## Stop development environment
	@echo "Stopping development environment..."
	cd deployment && $(DOCKER_COMPOSE_DEV) down
	@echo "✓ Development environment stopped"

# ============================================================================
# Docker - Production
# ============================================================================

docker-prod: ## Start production environment with Docker
	@echo "Starting production environment..."
	@test -f .env.production || (echo "Error: .env.production not found" && exit 1)
	cd deployment && $(DOCKER_COMPOSE_PROD) --env-file ../.env.production up -d
	@echo "✓ Production environment started"

docker-prod-build: ## Build and start production environment
	@echo "Building production environment..."
	@test -f .env.production || (echo "Error: .env.production not found" && exit 1)
	cd deployment && $(DOCKER_COMPOSE_PROD) --env-file ../.env.production up -d --build
	@echo "✓ Production environment built and started"

docker-prod-logs: ## View production logs
	cd deployment && $(DOCKER_COMPOSE_PROD) logs -f

docker-prod-stop: ## Stop production environment
	@echo "Stopping production environment..."
	cd deployment && $(DOCKER_COMPOSE_PROD) down
	@echo "✓ Production environment stopped"

docker-prod-restart: ## Restart production environment
	@echo "Restarting production environment..."
	cd deployment && $(DOCKER_COMPOSE_PROD) restart
	@echo "✓ Production environment restarted"

# ============================================================================
# Docker - Testing
# ============================================================================

docker-test: ## Run tests in Docker
	@echo "Running tests in Docker..."
	cd deployment && $(DOCKER_COMPOSE_TEST) up --abort-on-container-exit
	cd deployment && $(DOCKER_COMPOSE_TEST) down

# ============================================================================
# Docker - Management
# ============================================================================

docker-stop: ## Stop all Docker containers
	@echo "Stopping all containers..."
	cd deployment && $(DOCKER_COMPOSE_DEV) down
	cd deployment && $(DOCKER_COMPOSE_PROD) down
	@echo "✓ All containers stopped"

docker-clean: ## Remove all Docker containers, volumes, and images
	@echo "Cleaning Docker resources..."
	cd deployment && $(DOCKER_COMPOSE_DEV) down -v
	cd deployment && $(DOCKER_COMPOSE_PROD) down -v
	docker system prune -f
	@echo "✓ Docker resources cleaned"

docker-ps: ## Show running containers
	docker ps

docker-stats: ## Show container resource usage
	docker stats

# ============================================================================
# Database Management
# ============================================================================

db-backup: ## Backup MongoDB database
	@echo "Backing up database..."
	@mkdir -p backups
	docker exec aaris-mongodb-prod mongodump \
		--username=$${MONGODB_USERNAME} \
		--password=$${MONGODB_PASSWORD} \
		--authenticationDatabase=admin \
		--out=/data/backup
	docker cp aaris-mongodb-prod:/data/backup ./backups/backup-$$(date +%Y%m%d-%H%M%S)
	@echo "✓ Database backed up to backups/"

db-restore: ## Restore MongoDB database (usage: make db-restore BACKUP=backup-20240101-120000)
	@test -n "$(BACKUP)" || (echo "Error: BACKUP not specified. Usage: make db-restore BACKUP=backup-20240101-120000" && exit 1)
	@echo "Restoring database from $(BACKUP)..."
	docker cp ./backups/$(BACKUP) aaris-mongodb-prod:/data/restore
	docker exec aaris-mongodb-prod mongorestore \
		--username=$${MONGODB_USERNAME} \
		--password=$${MONGODB_PASSWORD} \
		--authenticationDatabase=admin \
		/data/restore
	@echo "✓ Database restored from $(BACKUP)"

db-shell: ## Open MongoDB shell
	docker exec -it aaris-mongodb-prod mongosh \
		--username=$${MONGODB_USERNAME} \
		--password=$${MONGODB_PASSWORD} \
		--authenticationDatabase=admin

# ============================================================================
# SSL Certificates
# ============================================================================

ssl-self-signed: ## Generate self-signed SSL certificate
	@echo "Generating self-signed SSL certificate..."
	@mkdir -p deployment/ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout deployment/ssl/key.pem \
		-out deployment/ssl/cert.pem \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
	@echo "✓ Self-signed certificate generated in deployment/ssl/"

ssl-check: ## Check SSL certificate expiry
	@test -f deployment/ssl/cert.pem || (echo "Error: Certificate not found" && exit 1)
	openssl x509 -in deployment/ssl/cert.pem -noout -dates

# ============================================================================
# Monitoring & Health
# ============================================================================

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -f http://localhost/health 2>/dev/null && echo "✓ Backend: healthy" || echo "✗ Backend: unhealthy"
	@curl -f http://localhost:3000/health 2>/dev/null && echo "✓ Frontend: healthy" || echo "✗ Frontend: unhealthy"

logs: ## View all logs
	@echo "Viewing logs..."
	tail -f logs/*.log

logs-backend: ## View backend logs
	tail -f logs/backend.log

logs-error: ## View error logs
	tail -f logs/error.log

logs-api: ## View API logs
	tail -f logs/api.log

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean temporary files and caches
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .tox dist build
	@echo "✓ Temporary files cleaned"

clean-logs: ## Clean log files
	@echo "Cleaning log files..."
	rm -f logs/*.log
	@echo "✓ Log files cleaned"

clean-all: clean clean-logs docker-clean ## Clean everything

# ============================================================================
# Deployment
# ============================================================================

deploy: ## Deploy to production
	@echo "Deploying to production..."
	./scripts/deploy.sh

deploy-check: ## Check production deployment readiness
	@echo "Checking deployment readiness..."
	@test -f .env.production || (echo "✗ .env.production not found" && exit 1)
	@test -f deployment/ssl/cert.pem || (echo "✗ SSL certificate not found" && exit 1)
	@test -f deployment/ssl/key.pem || (echo "✗ SSL key not found" && exit 1)
	@echo "✓ Deployment checks passed"

# ============================================================================
# Utilities
# ============================================================================

shell: ## Open Python shell with app context
	$(PYTHON) -i -c "from app.main import app; from app.services import *"

requirements: ## Update requirements.txt
	$(PIP) freeze > requirements.txt
	@echo "✓ requirements.txt updated"

env-example: ## Create .env.example from .env
	@test -f .env || (echo "Error: .env not found" && exit 1)
	@grep -v -E "^(OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|GROQ_API_KEY|JWT_SECRET|MONGODB_PASSWORD|SMTP_PASSWORD)=" .env > .env.example
	@echo "✓ .env.example created"

version: ## Show version information
	@echo "AARIS Version: 0.1.0"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"

# ============================================================================
# CI/CD
# ============================================================================

ci: install-dev lint test-coverage ## Run CI pipeline locally
	@echo "✓ CI pipeline completed"

pre-commit: format lint test ## Run pre-commit checks
	@echo "✓ Pre-commit checks passed"
