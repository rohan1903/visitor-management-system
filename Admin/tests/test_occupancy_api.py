"""
Test script for the real-time occupancy feature.
Run from the admin directory with your venv activated:
    cd admin
    python tests/test_occupancy_api.py
"""
import os
import sys
from pathlib import Path

# Ensure we're in admin and USE_MOCK_DATA so no Firebase needed
_admin_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_admin_dir))
os.chdir(_admin_dir)
os.environ.setdefault("USE_MOCK_DATA", "True")

def test_occupancy_api():
    try:
        from app import app
    except ImportError as e:
        print("ERROR: Could not import app. Activate your venv and install requirements.")
        print("  e.g. pip install -r requirements.txt")
        print(" ", e)
        return False

    with app.test_client() as client:
        r = client.get("/api/occupancy")
        print("GET /api/occupancy")
        print("  Status:", r.status_code)
        data = r.get_json()
        print("  Response:", data)

        if r.status_code != 200:
            print("FAIL: Expected status 200")
            return False
        if not data:
            print("FAIL: Empty response")
            return False
        if "current_occupancy" not in data:
            print("FAIL: Missing 'current_occupancy'")
            return False
        if "timestamp" not in data:
            print("FAIL: Missing 'timestamp'")
            return False
        if not isinstance(data["current_occupancy"], (int, float)):
            print("FAIL: current_occupancy should be a number")
            return False

    print("OK: API works as specified.")
    return True

if __name__ == "__main__":
    ok = test_occupancy_api()
    sys.exit(0 if ok else 1)
