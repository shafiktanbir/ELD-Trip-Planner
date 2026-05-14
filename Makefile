# ═══════════════════════════════════════════════════════════
#  ELD Trip Planner — Makefile
#  Run both backend and frontend with a single command
# ═══════════════════════════════════════════════════════════

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
VENV         := $(BACKEND_DIR)/venv
PYTHON       := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
MANAGE       := $(PYTHON) $(BACKEND_DIR)/manage.py

.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        migrate build clean lint

# ─── Default ────────────────────────────────────────────
help: ## Show this help
	@echo ""
	@echo "  🚛  ELD Trip Planner"
	@echo "  ────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Install ───────────────────────────────────────────
install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install Python dependencies + migrate
	@echo "📦 Setting up backend..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt -q
	$(MANAGE) migrate --run-syncdb
	@echo "✅ Backend ready"

install-frontend: ## Install Node dependencies
	@echo "📦 Setting up frontend..."
	cd $(FRONTEND_DIR) && npm install
	@echo "✅ Frontend ready"

# ─── Development ───────────────────────────────────────
dev: ## Run backend + frontend together (parallel)
	@echo "🚀 Starting ELD Trip Planner..."
	@echo "   Backend  → http://localhost:8000"
	@echo "   Frontend → http://localhost:5173"
	@echo ""
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## Run Django dev server (port 8000)
	$(MANAGE) runserver 0.0.0.0:8000

dev-frontend: ## Run Vite dev server (port 5173)
	cd $(FRONTEND_DIR) && npm run dev

# ─── Database ──────────────────────────────────────────
migrate: ## Run Django migrations
	$(MANAGE) migrate --run-syncdb

# ─── Build ─────────────────────────────────────────────
build: ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

# ─── Utilities ─────────────────────────────────────────
clean: ## Remove build artifacts and caches
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 Cleaned"

lint: ## Check code style
	@echo "Checking backend..."
	$(PYTHON) -m py_compile $(BACKEND_DIR)/trips/views.py
	$(PYTHON) -m py_compile $(BACKEND_DIR)/trips/services/hos_engine.py
	$(PYTHON) -m py_compile $(BACKEND_DIR)/trips/services/route_service.py
	$(PYTHON) -m py_compile $(BACKEND_DIR)/trips/services/eld_generator.py
	@echo "✅ No syntax errors"
