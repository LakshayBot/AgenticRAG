.PHONY: help build restore clean run migrate test docker-build docker-up docker-down

# Variables
PROJECT_PATH := src/RagSystem.ApiGateway
INFRA_PATH := src/RagSystem.Infrastructure
DOTNET := dotnet

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

restore: ## Restore NuGet packages
	$(DOTNET) restore

clean: ## Clean build artifacts
	$(DOTNET) clean
	find . -type d -name "bin" -o -name "obj" | xargs rm -rf

build: restore ## Build the solution
	$(DOTNET) build -c Release

run: ## Run the API Gateway locally
	cd $(PROJECT_PATH) && $(DOTNET) run

watch: ## Run with hot reload
	cd $(PROJECT_PATH) && $(DOTNET) watch run

migrate: ## Apply database migrations
	cd $(PROJECT_PATH) && $(DOTNET) ef database update --project ../$(INFRA_PATH)

migrate-add: ## Add a new migration (use NAME=MigrationName)
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make migrate-add NAME=YourMigrationName"; \
		exit 1; \
	fi
	cd $(PROJECT_PATH) && $(DOTNET) ef migrations add $(NAME) --project ../$(INFRA_PATH)

migrate-remove: ## Remove the last migration
	cd $(PROJECT_PATH) && $(DOTNET) ef migrations remove --project ../$(INFRA_PATH)

migrate-script: ## Generate SQL script for migrations
	cd $(PROJECT_PATH) && $(DOTNET) ef migrations script --project ../$(INFRA_PATH) --output migrations.sql

test: ## Run all tests
	$(DOTNET) test

test-coverage: ## Run tests with coverage
	$(DOTNET) test /p:CollectCoverage=true /p:CoverageReportsDirectory=./coverage

publish: ## Publish for deployment
	$(DOTNET) publish $(PROJECT_PATH) -c Release -o ./publish

docker-build: ## Build Docker image
	docker build -t rag-system-backend:latest .

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View logs from all containers
	docker-compose logs -f

docker-restart: ## Restart Docker services
	docker-compose restart

dev-setup: ## Setup development environment
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file"; fi
	@echo "Please update .env with your configuration"
	@echo "Then run: make migrate && make run"

check-health: ## Check API health
	@curl -s http://localhost:8000/health | jq '.'

format: ## Format code
	$(DOTNET) format

lint: ## Run code analysis
	$(DOTNET) build /p:TreatWarningsAsErrors=true
