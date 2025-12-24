#!/bin/bash

# Activate virtual environment and run Streamlit app
cd "$(dirname "$0")"
source venv/bin/activate

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "   The app will try to use Streamlit secrets if deployed,"
    echo "   but for local development, set it with:"
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    echo ""
fi

# Run Streamlit app
streamlit run app.py

