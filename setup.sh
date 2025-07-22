#!/bin/bash

echo "📦 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
echo "✅ Setup complete. Run the Flask API with: python backend/main.py"
