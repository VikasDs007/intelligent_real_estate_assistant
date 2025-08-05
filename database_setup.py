import os
import re
import sqlite3
import pandas as pd


def clean_col_names(df):
    """Cleans column names to be database-friendly."""
    cols = df.columns
    new_cols = [re.sub(r'[^A-Za-z0-9_]+', '', col).lower() for col in cols]
    df.columns = new_cols
    return df


def setup_database(excel_file_path='data/Real_Estate_data.xlsx', db_file_path='real_estate.db'):
    """
    Initializes the SQLite database.
    - Creates tables for clients and properties.
    - Loads initial data from the Excel file.
    """
    print("--- Starting Database Setup ---")

    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found at {excel_file_path}")

    # Connect to the SQLite database (this will create the file if it doesn't exist)
    conn = sqlite3.connect(db_file_path)
    print(f"Connected to database at '{db_file_path}'")

    # --- Load and Clean Data from Excel ---
    # Load and clean clients data
    try:
        clients_df = pd.read_excel(excel_file_path, sheet_name='Client_Database')
        clients_df = clean_col_names(clients_df)
        # Rename for clarity
        clients_df.rename(columns={'clientid': 'client_id', 'clientname': 'name',
                                   'clientphone': 'phone', 'clientemail': 'email'},
                          inplace=True)
    except Exception as e:
        conn.close()
        raise ValueError(f"Error loading clients data: {str(e)}")

    # Load and clean active listings data
    try:
        properties_df = pd.read_excel(excel_file_path, sheet_name='Active_Listings')
        properties_df = clean_col_names(properties_df)
        # Rename for clarity
        properties_df.rename(columns={'propertyid': 'property_id'}, inplace=True)
    except Exception as e:
        conn.close()
        raise ValueError(f"Error loading properties data: {str(e)}")

    # --- Write Data to SQLite Tables ---
    try:
        # The 'if_exists='replace'' will drop the table first if it exists and create a new one.
        # This is useful for re-running the script during development.
        clients_df.to_sql('clients', conn, if_exists='replace', index=False)
        print("Successfully created 'clients' table and loaded data.")

        properties_df.to_sql('properties', conn, if_exists='replace', index=False)
        print("Successfully created 'properties' table and loaded data.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    setup_database()
    print("\n--- Database setup is complete! ---")
    print("A new file 'real_estate.db' should now be in your project folder.")