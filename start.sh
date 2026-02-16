#!/bin/bash

# Bluecore Campaign App - Easy Start Script

echo "=========================================="
echo "Campaign Data Update Application"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "WARNING: docker-compose not found, trying 'docker compose' instead..."
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "Starting application with Docker..."
echo ""

# Stop any existing containers
echo "Stopping any existing containers..."
$COMPOSE_CMD down 2>/dev/null

# Build and start
echo "Building and starting the application..."
$COMPOSE_CMD up --build -d

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Application started successfully!"
    echo "=========================================="
    echo ""
    echo "Access the application at: http://localhost:5000"
    echo ""
    echo "To view logs, run:"
    echo "  $COMPOSE_CMD logs -f"
    echo ""
    echo "To stop the application, run:"
    echo "  $COMPOSE_CMD down"
    echo ""
else
    echo ""
    echo "ERROR: Failed to start the application"
    echo "Check the error messages above for details"
    exit 1
fi
