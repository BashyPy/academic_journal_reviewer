#!/bin/bash

echo "Setting up AARIS - Academic Journal Reviewer"

# Create virtual environment
uv venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Setup frontend
cd frontend
npm install
cd ..

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please configure your Firebase and Gemini API credentials."
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with Firebase and Gemini API credentials"
echo "2. Run the backend: python run.py"
echo "3. Run the frontend: cd frontend && npm start"