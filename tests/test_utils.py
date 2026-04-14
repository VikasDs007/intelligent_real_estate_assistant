import sys
import os

# Add the parent directory to sys.path to import modules from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import sqlite3
import utils  # Add this to access the module
from utils import format_indian_currency, get_recommendations, add_task, find_budget

def test_format_indian_currency():
    assert format_indian_currency(1000000) == '10,00,000'
    assert format_indian_currency(5000) == '5,000'
    assert format_indian_currency(None) == 'N/A'

def test_find_budget():
    assert find_budget('Budget 10L') == 1000000
    assert find_budget('Rent 5000') == 5000
    assert find_budget('No budget mentioned') == 0

def test_get_recommendations(temp_db):
    cursor = temp_db.cursor()
    cursor.execute("ALTER TABLE clients ADD COLUMN name TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN phone TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN email TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN lookingfor TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN requirements TEXT")
    cursor.execute(
        "UPDATE clients SET name=?, phone=?, email=?, lookingfor=?, requirements=? WHERE client_id='CL-TEST'",
        ("Test User", "9876543210", "test@example.com", "Sale", "2 BHK Budget 50L in Mira Road")
    )
    cursor.execute(
        "CREATE TABLE properties (property_id TEXT PRIMARY KEY, listingtype TEXT, bedroomsbhk TEXT, arealocality TEXT, askingprice REAL, monthlyrent REAL)"
    )
    cursor.execute(
        "INSERT INTO properties (property_id, listingtype, bedroomsbhk, arealocality, askingprice, monthlyrent) VALUES (?, ?, ?, ?, ?, ?)",
        ("SALE-PROP-1001", "Sale", "2 BHK", "Mira Road", 4800000, 0)
    )
    temp_db.commit()

    result = get_recommendations('CL-TEST')
    assert isinstance(result, dict)
    assert 'message' in result
    assert 'client_details' in result
    assert 'recommendations' in result
    assert isinstance(result['recommendations'], list)
    assert len(result['recommendations']) > 0  # Ensure recommendations are returned
    # Example: Check a specific field in the first recommendation
    if result['recommendations']:
        assert 'property_id' in result['recommendations'][0]


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / 'test.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE clients (client_id TEXT PRIMARY KEY, status TEXT)"
    )
    cursor.execute(
        "CREATE TABLE tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, property_id TEXT, task_type TEXT, task_description TEXT, due_date TEXT, status TEXT, details TEXT)"
    )
    cursor.execute("INSERT INTO clients (client_id, status) VALUES ('CL-TEST', 'New')")    
    conn.commit()
    original_db = utils.DB_FILE_PATH  # Use utils.DB_FILE_PATH
    utils.DB_FILE_PATH = str(db_path)  # Temporarily override
    yield conn
    utils.DB_FILE_PATH = original_db  # Restore original
    conn.close()

def test_add_task(temp_db):
    add_task('CL-TEST', 'Site Visit', 'Visit property XYZ', '2023-12-31', property_id='PROP-001')
    cursor = temp_db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE client_id = 'CL-TEST'")
    task = cursor.fetchone()
    assert task is not None
    assert task[3] == 'Site Visit'  # task_type
    assert task[4] == 'Visit property XYZ'  # task_description
    assert task[5] == '2023-12-31'  # due_date
    assert task[6] == 'Pending'  # status
    cursor.execute("SELECT status FROM clients WHERE client_id = 'CL-TEST'")
    status = cursor.fetchone()[0]
    assert status == 'Site Visit Planned'