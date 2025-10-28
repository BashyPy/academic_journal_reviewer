#!/bin/bash

echo "Starting AARIS Backend..."

# Activate virtual environment
source .venv/bin/activate

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from template..."
    cp .env.example .env
    echo "Please configure your API keys in .env file"
fi

# Start the backend
echo "Backend starting on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
python run.py