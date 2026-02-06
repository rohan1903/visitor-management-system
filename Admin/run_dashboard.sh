#!/bin/bash

echo "=========================================="
echo "Admin Dashboard - Setup & Run"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install --user Flask firebase-admin pandas openpyxl python-dotenv scikit-learn 2>&1 | grep -v "already satisfied" || echo "Dependencies installed (or already present)"
echo ""

# Check if port 5000 is available
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 5000 is already in use!"
    echo "   Please stop the process using port 5000 or use a different port"
    exit 1
else
    echo "✅ Port 5000 is available"
fi

echo ""
echo "=========================================="
echo "Starting Admin Dashboard..."
echo "=========================================="
echo ""
echo "🌐 Dashboard will be available at: http://localhost:5000"
echo ""
echo "Note: Using mock data (no Firebase credentials required)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the app
python3 app.py

