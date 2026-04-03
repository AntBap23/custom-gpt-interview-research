#!/bin/bash

# Activate virtual environment and run FastAPI + static frontend
cd "$(dirname "$0")"
if [ -f .venv/bin/activate ]; then
  # Created by: python install.py
  source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
  source venv/bin/activate
else
  echo "No .venv or venv found. Run: python install.py"
  exit 1
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "   For local development, set it with:"
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    echo ""
fi

echo "Starting Qualitative AI Interview Studio (FastAPI)..."
echo "Open: http://127.0.0.1:8000"
echo ""

# Run backend (serves /frontend and page routes)
python -m uvicorn backend.main:app --reload
