#!/bin/bash

# Quick Start Script for Visitor Management System
# This script helps you start the applications for screenshots

echo "=========================================="
echo "Visitor Management System - Quick Start"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $1 is already in use!"
        return 1
    else
        echo "✅ Port $1 is available"
        return 0
    fi
}

# Check ports
echo "Checking ports..."
check_port 5000
check_port 5001
check_port 5002
echo ""

# Instructions
echo "=========================================="
echo "INSTRUCTIONS:"
echo "=========================================="
echo ""
echo "You need to run 3 applications in SEPARATE terminal windows:"
echo ""
echo "Terminal 1 - Register App (Port 5001):"
echo "  cd Register_App"
echo "  python3 app.py"
echo "  → Access at: http://localhost:5001"
echo ""
echo "Terminal 2 - Admin Dashboard (Port 5000):"
echo "  cd Admin"
echo "  python3 app.py"
echo "  → Access at: http://localhost:5000"
echo ""
echo "Terminal 3 - Webcam Check-in (Port 5002):"
echo "  cd Webcam"
echo "  python3 app.py"
echo "  → Access at: http://localhost:5002"
echo ""
echo "=========================================="
echo ""
echo "After starting all apps, open your browser and:"
echo "1. Take screenshot of http://localhost:5001 (Registration)"
echo "2. Take screenshot of http://localhost:5000 (Admin Dashboard)"
echo "3. Take screenshot of http://localhost:5002 (Check-in)"
echo ""
echo "Press Ctrl+C to exit this script"
echo ""

# Ask if user wants to start apps
read -p "Do you want to start Register App now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting Register App..."
    cd Register_App
    python3 app.py
fi

