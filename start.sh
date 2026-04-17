#!/bin/bash
set -e

cd "$(dirname "$0")"

# Kill any existing servers on these ports
pkill -f "research-server.py" 2>/dev/null || true
pkill -f "expo start" 2>/dev/null || true
sleep 1

# Load environment variables
set -a
source .env
set +a

echo "Starting Petrarca backend server..."
venv/bin/python3 scripts/research-server.py &
BACKEND_PID=$!

echo "Starting Expo frontend..."
cd app && node_modules/.bin/expo start --web &
FRONTEND_PID=$!

echo ""
echo "Petrarca is running!"
echo "  App:    http://localhost:8081"
echo "  Server: http://localhost:8090"
echo ""
echo "Press Ctrl+C to stop both servers."

# On Ctrl+C, kill both servers by name (catches subprocesses too)
trap "echo 'Stopping...'; pkill -f 'research-server.py'; pkill -f 'expo start'; exit 0" INT TERM

wait
