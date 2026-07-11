#!/bin/bash

# QuantifI Virtual Environment Setup Script
# Usage: bash scripts/setup_venv.sh [uv|pip]

set -e

echo "🚀 Setting up QuantifI virtual environment..."

# Default to UV if no argument provided
MODE="${1:-uv}"

echo "📋 Mode: $MODE"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔑 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies based on mode
if [ "$MODE" = "uv" ]; then
    echo "📦 Installing dependencies with UV..."
    if command -v uv &> /dev/null; then
        uv sync
        echo "✅ UV dependencies installed successfully!"
    else
        echo "❌ UV not found. Please install UV first:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "   Then run: source .venv/bin/activate && uv sync"
        exit 1
    fi
elif [ "$MODE" = "pip" ]; then
    echo "📦 Installing dependencies with pip..."
    python3 -m pip install -r requirements.txt
    echo "✅ Pip dependencies installed successfully!"
else
    echo "❌ Invalid mode: $MODE. Use 'uv' or 'pip'"
    exit 1
fi

echo "🎉 Setup complete!"
echo "💡 Next steps:"
echo "   1. Configure Streamlit secrets in .streamlit/secrets.toml"
echo "   2. Run the app: streamlit run app.py"
echo "   3. Set up database schema (see README.md)"

echo "📝 Virtual environment activated. Type 'deactivate' to exit."