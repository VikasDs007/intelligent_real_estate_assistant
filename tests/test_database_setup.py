import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import sqlite3
import pandas as pd
from database_setup import setup_database, clean_col_names  # Corrected function name

def test_clean_col_names():
    df = pd.DataFrame(columns=['Column 1', 'Column-2'])
    cleaned_df = clean_col_names(df)
    assert list(cleaned_df.columns) == ['column1', 'column2']  # Based on re.sub removing non-alphanumeric

def test_setup_database(tmp_path):
    db_path = tmp_path / 'test.db'
    setup_database(db_file_path=str(db_path))  # Pass db_path
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    assert ('clients',) in tables
    assert ('properties',) in tables
    conn.close()