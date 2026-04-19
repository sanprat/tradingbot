#!/bin/bash
# Deploy script for TradingBot to VPS

echo "=== TradingBot Deploy ==="

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    echo "Running as root - good"
else
    echo "Note: Some commands may require sudo"
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found! Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose not found!"
    exit 1
fi

echo "Docker found: $(docker --version)"

# Create directory structure
echo "Creating /home/tradingbot..."
mkdir -p /home/tradingbot
mkdir -p /home/tradingbot/data

# Copy files
echo "Copying files to /home/tradingbot..."
cp -r app/ /home/tradingbot/
cp -r .env.example /home/tradingbot/.env
cp requirements.txt /home/tradingbot/
cp Dockerfile /home/tradingbot/
cp docker-compose.yml /home/tradingbot/

# Create .env if it doesn't exist
if [ ! -f /home/tradingbot/.env ]; then
    cp /home/tradingbot/.env.example /home/tradingbot/.env
    echo "Created .env from template - EDIT IT BEFORE RUNNING!"
fi

cd /home/tradingbot

# Build and start
echo "Building Docker container..."
docker-compose build

echo "Starting TradingBot..."
docker-compose up -d

echo ""
echo "=== Deployed! ==="
echo "Container: tradingbot"
echo "Port: 8002"
echo "Logs: docker logs tradingbot"
echo "Status: docker ps | grep tradingbot"