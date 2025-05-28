#!/bin/bash

echo "📦 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Setup complete. Run with: streamlit run app.py"
