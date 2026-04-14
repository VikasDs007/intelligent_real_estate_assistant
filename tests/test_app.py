import sys
import os
import sqlite3
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import api
from fastapi.testclient import TestClient


@pytest.fixture
def test_client(tmp_path):
    db_path = tmp_path / "test_api.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE clients (client_id TEXT PRIMARY KEY, name TEXT, phone TEXT, email TEXT, lookingfor TEXT, requirements TEXT, status TEXT)"
    )
    cursor.execute(
        "CREATE TABLE properties (property_id TEXT PRIMARY KEY, listingtype TEXT, bedroomsbhk TEXT, arealocality TEXT, askingprice REAL, monthlyrent REAL)"
    )
    cursor.execute(
        "INSERT INTO clients (client_id, name, phone, email, lookingfor, requirements, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("CL-1001", "Test User", "9876543210", "test@example.com", "Sale", "2 BHK Budget 50L in Mira Road", "New")
    )
    cursor.execute(
        "INSERT INTO properties (property_id, listingtype, bedroomsbhk, arealocality, askingprice, monthlyrent) VALUES (?, ?, ?, ?, ?, ?)",
        ("SALE-PROP-1001", "Sale", "2 BHK", "Mira Road", 4800000, 0)
    )
    conn.commit()
    conn.close()

    original_path = api.DB_FILE_PATH
    api.DB_FILE_PATH = str(db_path)
    try:
        yield TestClient(api.api_app)
    finally:
        api.DB_FILE_PATH = original_path

def test_read_root():
    response = TestClient(api.api_app).get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "API is running"}

# Add more tests for other endpoints as needed
def test_get_clients(test_client):
    response = test_client.get("/clients")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_client_success(test_client):
    payload = {
        "name": "Priya Shah",
        "phone": "9123456789",
        "email": "priya@example.com",
        "looking_for": "Rent",
        "requirements": "2 BHK Rent 25000 in Andheri",
    }
    response = test_client.post("/clients", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Client added successfully!"
    assert body["client_id"].startswith("CL-")


def test_create_client_invalid_payload_returns_422(test_client):
    payload = {
        "name": "Invalid",
        "phone": "123",
        "email": "not-an-email",
        "looking_for": "Lease",
        "requirements": "Any",
    }
    response = test_client.post("/clients", json=payload)
    assert response.status_code == 422


def test_update_client_success(test_client):
    payload = {
        "name": "Test User Updated",
        "phone": "9988776655",
        "email": "updated@example.com",
        "looking_for": "Sale",
        "requirements": "2 BHK Budget 55L in Mira Road",
        "status": "Negotiating",
    }
    response = test_client.put("/clients/CL-1001", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Client updated successfully!"

    details = test_client.get("/clients/CL-1001")
    assert details.status_code == 200
    assert details.json()["status"] == "Negotiating"
    assert details.json()["phone"] == "9988776655"


def test_update_client_not_found_returns_404(test_client):
    payload = {
        "name": "Ghost User",
        "phone": "9988776655",
        "email": "ghost@example.com",
        "looking_for": "Sale",
        "requirements": "2 BHK Budget 55L in Mira Road",
        "status": "New",
    }
    response = test_client.put("/clients/CL-9999", json=payload)
    assert response.status_code == 404


def test_delete_client_success_and_repeat_returns_404(test_client):
    response = test_client.delete("/clients/CL-1001")
    assert response.status_code == 200
    assert response.json()["message"] == "Client deleted successfully!"

    second_delete = test_client.delete("/clients/CL-1001")
    assert second_delete.status_code == 404


def test_recommendations_for_missing_client_returns_404(test_client):
    response = test_client.get("/recommendations/CL-9999")
    assert response.status_code == 404


def test_recommendations_no_matches_returns_empty(test_client):
    create_response = test_client.post(
        "/clients",
        json={
            "name": "Hard Match",
            "phone": "9876501234",
            "email": "hardmatch@example.com",
            "looking_for": "Sale",
            "requirements": "5 BHK Budget 1L in Unknown",
        },
    )
    assert create_response.status_code == 200
    client_id = create_response.json()["client_id"]

    rec_response = test_client.get(f"/recommendations/{client_id}")
    assert rec_response.status_code == 200
    body = rec_response.json()
    assert body["recommendations"] == []
    assert body["message"] == "No suitable properties found."


def test_recommendations_success(test_client):
    response = test_client.get("/recommendations/CL-1001")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "recommendations" in body
    assert len(body["recommendations"]) > 0