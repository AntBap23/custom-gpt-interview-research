#!/bin/bash

# Activate virtual environment and run NiceGUI app
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

# Run NiceGUI app
python app.py
