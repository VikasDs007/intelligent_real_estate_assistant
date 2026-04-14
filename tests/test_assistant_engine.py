import os
import sqlite3
import sys
from datetime import date

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import assistant_engine
import utils


@pytest.fixture
def assistant_db(tmp_path, monkeypatch):
    db_path = tmp_path / "assistant.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE clients (client_id TEXT PRIMARY KEY, name TEXT, phone TEXT, email TEXT, lookingfor TEXT, requirements TEXT, status TEXT)"
    )
    cursor.execute(
        "CREATE TABLE properties (property_id TEXT PRIMARY KEY, listingtype TEXT, listingdate TEXT, buildingsociety TEXT, arealocality TEXT, city TEXT, pincode INTEGER, propertytype TEXT, bedroomsbhk TEXT, bathrooms INTEGER, areasqft INTEGER, areatype TEXT, floornumber INTEGER, totalfloors INTEGER, furnishing TEXT, facingdirection TEXT, parkingcars INTEGER, propertyageyrs INTEGER, amenities TEXT, askingprice REAL, monthlyrent REAL, securitydeposit REAL, maintmonth REAL, pricenegotiable TEXT, commission INTEGER, ownername TEXT, ownerphone TEXT)"
    )
    cursor.execute(
        "CREATE TABLE communication_log (log_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, timestamp TEXT, note TEXT)"
    )
    cursor.execute(
        "CREATE TABLE tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, property_id TEXT, task_type TEXT, task_description TEXT, due_date TEXT, details TEXT, status TEXT)"
    )
    cursor.execute(
        "INSERT INTO clients (client_id, name, phone, email, lookingfor, requirements, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("CL-1001", "Asha Mehta", "9876543210", "asha@example.com", "Sale", "2 BHK Budget 50L in Mira Road", "New"),
    )
    cursor.execute(
        "INSERT INTO properties (property_id, listingtype, listingdate, buildingsociety, arealocality, city, pincode, propertytype, bedroomsbhk, bathrooms, areasqft, areatype, floornumber, totalfloors, furnishing, facingdirection, parkingcars, propertyageyrs, amenities, askingprice, monthlyrent, securitydeposit, maintmonth, pricenegotiable, commission, ownername, ownerphone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("SALE-PROP-1001", "Sale", "2026-04-01", "Harmony Heights", "Mira Road", "Mumbai", 401107, "Apartment", "2 BHK", 2, 950, "Carpet", 5, 12, "Semi-Furnished", "East", 1, 4, "Gymnasium, 24x7 Security", 4800000, None, None, None, "Yes", 1, "Raj Patel", "9999999999"),
    )
    cursor.execute(
        "INSERT INTO tasks (client_id, property_id, task_type, task_description, due_date, details, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("CL-1001", "SALE-PROP-1001", "Site Visit", "Visit the shortlisted apartment", "2026-04-20", None, "Pending"),
    )
    conn.commit()
    conn.close()

    original_db = utils.DB_FILE_PATH
    monkeypatch.setattr(utils, "DB_FILE_PATH", str(db_path))
    monkeypatch.setattr(assistant_engine, "AI_API_KEY", "")
    yield db_path
    monkeypatch.setattr(utils, "DB_FILE_PATH", original_db)


def test_detect_intent_for_tasks():
    assert assistant_engine.detect_intent("Show follow-up tasks") == "tasks"


def test_build_context_includes_selected_records(assistant_db):
    context = assistant_engine.build_context("CL-1001", "SALE-PROP-1001")
    assert context["overview"]["total_clients"] == 1
    assert context["selected_client"]["client_id"] == "CL-1001"
    assert context["selected_property"]["property_id"] == "SALE-PROP-1001"


def test_generate_assistant_reply_uses_local_mode(assistant_db):
    reply = assistant_engine.generate_assistant_reply(
        "Recommend properties for this client",
        selected_client_id="CL-1001",
        selected_property_id="SALE-PROP-1001",
    )
    assert reply["used_ai"] is False
    assert reply["intent"] == "recommendations"
    assert "matching properties" in reply["answer"].lower() or "best match" in reply["answer"].lower()
    assert reply["suggested_actions"]


def test_handle_chat_request_opens_client_record(assistant_db):
    reply = assistant_engine.handle_chat_request("show client CL-1001")
    assert reply["action"]["type"] == "focus_client"
    assert reply["action"]["client_id"] == "CL-1001"
    assert reply["intent"] == "client"


def test_handle_chat_request_resolves_client_name(assistant_db):
    reply = assistant_engine.handle_chat_request("show asha")
    assert reply["action"]["type"] == "focus_client"
    assert reply["action"]["client_id"] == "CL-1001"


def test_handle_chat_request_saves_note(assistant_db):
    reply = assistant_engine.handle_chat_request("add note for CL-1001: call tomorrow")
    assert reply["action"]["type"] == "focus_client"
    assert reply["action"]["client_id"] == "CL-1001"

    conn = sqlite3.connect(assistant_db)
    rows = conn.execute("SELECT note FROM communication_log WHERE client_id = ?", ("CL-1001",)).fetchall()
    conn.close()
    assert rows
    assert rows[0][0] == "call tomorrow"


def test_handle_chat_request_creates_task(assistant_db):
    reply = assistant_engine.handle_chat_request("create task for CL-1001 tomorrow: site visit")
    assert reply["action"]["type"] == "focus_client"
    assert reply["action"]["client_id"] == "CL-1001"

    conn = sqlite3.connect(assistant_db)
    row = conn.execute(
        "SELECT task_type, task_description, due_date, status FROM tasks WHERE client_id = ? ORDER BY task_id DESC LIMIT 1",
        ("CL-1001",),
    ).fetchone()
    conn.close()
    assert row[0] in {"Follow-up", "Site Visit"}
    assert "site visit" in row[1].lower()
    assert row[2] == "2026-04-15"
    assert row[3] == "Pending"


def test_save_client_note_persists_to_log(assistant_db):
    result = assistant_engine.save_client_note("CL-1001", "Call back after site visit.")
    assert result["status"] == "saved"

    conn = sqlite3.connect(assistant_db)
    rows = conn.execute("SELECT note FROM communication_log WHERE client_id = ?", ("CL-1001",)).fetchall()
    conn.close()
    assert rows
    assert rows[0][0] == "Call back after site visit."


def test_create_follow_up_task_persists_to_tasks(assistant_db):
    result = assistant_engine.create_follow_up_task(
        client_id="CL-1001",
        task_description="Follow up on shortlisted apartment",
        due_date=date(2026, 4, 22),
        property_id="SALE-PROP-1001",
        task_type="Follow-up",
        details="Assistant-created task",
    )
    assert result["status"] == "created"
    assert result["property_id"] == "SALE-PROP-1001"

    conn = sqlite3.connect(assistant_db)
    row = conn.execute(
        "SELECT client_id, property_id, task_type, task_description, due_date, details, status FROM tasks WHERE client_id = ? ORDER BY task_id DESC LIMIT 1",
        ("CL-1001",),
    ).fetchone()
    conn.close()
    assert row[0] == "CL-1001"
    assert row[1] == "SALE-PROP-1001"
    assert row[2] == "Follow-up"
    assert row[3] == "Follow up on shortlisted apartment"
    assert row[4] == "2026-04-22"
    assert row[5] == "Assistant-created task"
    assert row[6] == "Pending"
