import re
import sqlite3
import subprocess
import sys
import threading
import time
import requests
import streamlit as st
import uvicorn
from api import api_app  # Import from new api.py file
from sqlalchemy import create_engine


"""
Intelligent Real Estate Assistant Application

This script runs both the FastAPI backend API and the Streamlit frontend.
"""

# --- 1. BACKEND (FASTAPI) CODE ---

api_app = FastAPI(title="Real Estate API")
DB_FILE_PATH = "real_estate.db"

# Pydantic Models, API endpoints etc. remain the same...
class ClientUpdate(BaseModel):
    name: str
    phone: str
    email: str
    looking_for: str
    requirements: str
    status: str


class ClientCreate(BaseModel):
    name: str
    phone: str
    email: str
    looking_for: str
    requirements: str


@api_app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}


@api_app.get("/clients")
def get_all_clients():
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            return pd.read_sql("SELECT client_id, name FROM clients", conn).to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@api_app.get("/clients/{client_id}")
def get_client_details(client_id: str):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        client_details = pd.read_sql(f"SELECT * FROM clients WHERE client_id = '{client_id}'", conn)
        if client_details.empty: raise HTTPException(status_code=404, detail="Client not found")
        return client_details.iloc[0].to_dict()


@api_app.post("/clients")
def create_client(client: ClientCreate):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        last_id_row = cursor.execute("SELECT client_id FROM clients ORDER BY CAST(SUBSTR(client_id, 4) AS INTEGER) DESC LIMIT 1").fetchone()
        last_id = int(last_id_row[0].split('-')[1]) if last_id_row else 1000
        new_client_id = f"CL-{last_id + 1}"
        cursor.execute("INSERT INTO clients (client_id, name, phone, email, lookingfor, requirements, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (new_client_id, client.name, client.phone, client.email, client.looking_for, client.requirements, "New"))
        conn.commit()
        return {"message": "Client added successfully!", "client_id": new_client_id}


@api_app.put("/clients/{client_id}")
def update_client(client_id: str, client: ClientUpdate):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET name=?, phone=?, email=?, lookingfor=?, requirements=?, status=? WHERE client_id=?", (client.name, client.phone, client.email, client.looking_for, client.requirements, client.status, client_id))
        conn.commit()
        if cursor.rowcount == 0: raise HTTPException(status_code=404, detail="Client not found")
        return {"message": "Client updated successfully!", "client_id": client_id}


@api_app.delete("/clients/{client_id}")
def delete_client(client_id: str):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
        conn.commit()
        if cursor.rowcount == 0: raise HTTPException(status_code=404, detail="Client not found")
        return {"message": "Client deleted successfully!", "client_id": client_id}


@api_app.get("/recommendations/{client_id}")
def get_recommendations_for_client(client_id: str):
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            clients_df = pd.read_sql(f"SELECT * FROM clients WHERE client_id = '{client_id}'", conn)
            properties_df = pd.read_sql("SELECT * FROM properties", conn)
        if clients_df.empty:
            raise HTTPException(status_code=404, detail="Client not found.")
        client_data = clients_df.iloc[0]
        properties_df['bhk'] = properties_df['bedroomsbhk'].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
        def find_budget(text):
            match = re.search(r'Budget[^\d]*([\d,]+)L?', str(text), re.IGNORECASE)
            if match:
                return int(match.group(1).replace(',', '')) * 100000
            match_rent = re.search(r'Rent[^\d]*([\d,]+)', str(text), re.IGNORECASE)
            if match_rent:
                return int(match_rent.group(1).replace(',', ''))
            return 0
        def find_location(text):
            match = re.search(r'\bin\s+([\w\s]+)', str(text), re.IGNORECASE)
            if match:
                loc = match.group(1).strip()
                return 'Any' if 'anywhere' in loc.lower() else loc
            return 'Any'
        req_budget = find_budget(client_data['requirements'])
        req_locality = find_location(client_data['requirements'])
        # Safely extract BHK, default to 0 if not found
        bhk_match = re.search(r'(\d+)\s*BHK', str(client_data['requirements']))
        req_bhk = int(bhk_match.group(1)) if bhk_match else 0
        matches = properties_df[properties_df['listingtype'].str.lower() == client_data['lookingfor'].lower()]
        matches = matches[matches['bhk'] >= req_bhk]
        budget_ceil = req_budget * 1.10
        if client_data['lookingfor'].lower() == 'sale':
            matches = matches[matches['askingprice'] <= budget_ceil]
        else:
            matches = matches[matches['monthlyrent'] <= budget_ceil]
        final_matches = pd.DataFrame()
        if req_locality != 'Any':
            strict_matches = matches[matches['arealocality'].str.contains(req_locality, case=False)]
            if not strict_matches.empty:
                final_matches = strict_matches
        message = "Perfect matches found."
        if final_matches.empty:
            message = "No exact location match. Showing best matches from other areas."
            final_matches = matches
        if final_matches.empty:
            return {"message": "No suitable properties found.", "recommendations": []}
        results = final_matches.head(5).to_dict(orient='records')
        return {"message": message, "client_details": client_data.to_dict(), "recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

# --- Function to run the API server ---
def run_api():
    uvicorn.run(api_app, host='0.0.0.0', port=8000)

# --- CORRECTED LOGIC TO START THE API SERVER ---
# This code will run at the start of the Streamlit script
if 'api_started' not in st.session_state:
    try:
        # Check if API is already running
        requests.get("http://127.0.0.1:8000/")
        print("API is already running.")
    except requests.exceptions.ConnectionError:
        print("Starting API server in a background thread...")
        api_thread = threading.Thread(target=run_api)
        api_thread.daemon = True
        api_thread.start()
        time.sleep(4)  # Give the server a moment to start
    st.session_state.api_started = True


# --- 2. FRONTEND (STREAMLIT) CODE ---
# The rest of the file is the Streamlit UI code, which is correct and unchanged.

if __name__ == "__main__":
    st.set_page_config(page_title="Intelligent Real Estate Assistant", page_icon="🏠", layout="wide")
    st.title("🏠 Intelligent Real Estate Assistant")
    st.markdown("---")
    API_BASE_URL = "http://127.0.0.1:8000"  # Changed from 8001 to match backend port

# Main App Logic
st.header("Client Recommendations")

# Use a two-column layout
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Select a Client")
    try:
        client_list_response = requests.get(f"{API_BASE_URL}/clients")
        client_list_response.raise_for_status()
        client_list = client_list_response.json()
        client_display_list = [f"{c['client_id']} - {c['name']}" for c in client_list]
        selected_client_str = st.selectbox("Choose a client:", options=client_display_list)
    except requests.exceptions.RequestException:
        st.warning("Waiting for API... The app will refresh shortly.")
        time.sleep(3)
        st.rerun()

    if selected_client_str:
        client_id = selected_client_str.split(' - ')[0]
        client_details_response = requests.get(f"{API_BASE_URL}/clients/{client_id}")
        client_details = client_details_response.json()
        st.text_area("Client Requirements", value=client_details['requirements'], height=150, disabled=True)

with col2:
    st.subheader("Recommended Properties")
    if selected_client_str:
        client_id = selected_client_str.split(' - ')[0]
        try:
            recs_response = requests.get(f"{API_BASE_URL}/recommendations/{client_id}")
            recs_response.raise_for_status()
            data = recs_response.json()
            st.caption(data.get("message", ""))
            if data.get("recommendations"):
                df_recs = pd.DataFrame(data["recommendations"])
                st.dataframe(df_recs, use_container_width=True)
            else:
                st.info("No matching properties found for this client.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching recommendations: {str(e)}")