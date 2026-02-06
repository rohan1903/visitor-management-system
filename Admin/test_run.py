#!/usr/bin/env python3
"""Quick test script to check if the app can start"""

import sys

print("Testing imports...")
try:
    from flask import Flask
    print("✅ Flask imported successfully")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    print("   Install with: pip3 install Flask")
    sys.exit(1)

try:
    import pandas
    print("✅ pandas imported successfully")
except ImportError as e:
    print(f"⚠️  pandas import failed: {e}")
    print("   Install with: pip3 install pandas")

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv imported successfully")
except ImportError as e:
    print(f"⚠️  python-dotenv import failed: {e}")
    print("   Install with: pip3 install python-dotenv")

print("\nTesting app.py import...")
try:
    import app
    print("✅ app.py imported successfully")
    print("\n✅ All checks passed! You can run: python3 app.py")
except Exception as e:
    print(f"❌ Error importing app.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

