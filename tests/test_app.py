import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import api_app  # Updated to import from api.py
from fastapi.testclient import TestClient

client = TestClient(api_app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API is running"}

# Add more tests for other endpoints as needed
def test_get_clients():
    response = client.get("/clients")
    assert response.status_code == 200
    assert isinstance(response.json(), list)