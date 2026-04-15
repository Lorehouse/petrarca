#!/bin/bash
set -e

cd "$(dirname "$0")"

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

# On Ctrl+C, kill both servers
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
