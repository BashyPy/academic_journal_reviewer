#!/bin/bash

echo "Starting AARIS with Docker..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please configure your API keys before running."
    exit 1
fi

# Build and start services
docker-compose up --build -d

echo "AARIS is starting up..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "MongoDB: localhost:27017"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"