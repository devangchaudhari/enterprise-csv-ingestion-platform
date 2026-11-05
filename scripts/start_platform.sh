#!/usr/bin/env bash
set -e

echo "======================================================================"
echo " Starting OmniRetail Enterprise Data Hub & Orchestration Platform"
echo "======================================================================"

# Root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Activate Python virtual environment
if [ -d ".venv" ]; then
    echo " Activating Python virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo " Error: .venv virtual environment not found. Please create one with: python3 -m venv .venv"
    exit 1
fi

export PYTHONPATH="$ROOT_DIR"

# 2. Initialize and Seed Enterprise Database
echo " Initializing schema and seeding retail data..."
python3 -m backend.app.seeds.seed_data

# 3. Run Automated Validation Test Suite
echo " Executing Pytest & Vitest automated test suites..."
PYTHONPATH=. pytest backend/tests/ -v

# 4. Check Frontend build
if [ ! -d "frontend/node_modules" ]; then
    echo " Installing frontend dependencies..."
    (cd frontend && npm install)
fi

echo "======================================================================"
echo " Starting Services Locally:"
echo "   Backend REST API:     http://127.0.0.1:8000"
echo "   API Swagger Docs:     http://127.0.0.1:8000/api/v1/docs"
echo "   Frontend Web UI:      http://localhost:3000"
echo "======================================================================"
echo " Default Personas:"
echo "   Administrator:  admin@retailhub.enterprise / AdminSecret2026!"
echo "   Data Engineer:  engineer@retailhub.enterprise / EngineerSecret2026!"
echo "   Ops Engineer:   ops@retailhub.enterprise / OpsSecret2026!"
echo "   Viewer:         viewer@retailhub.enterprise / ViewerSecret2026!"
echo "======================================================================"

# Start backend in background and frontend in foreground
echo " Launching FastAPI backend on http://127.0.0.1:8000..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

trap "echo 'Stopping services...'; kill $BACKEND_PID 2>/dev/null || true; exit" SIGINT SIGTERM

echo " Launching Next.js frontend on http://localhost:3000..."
cd frontend
npm run dev
