import re
import sqlite3
from pydantic import BaseModel
import pandas as pd
from fastapi import FastAPI, HTTPException

DB_FILE_PATH = "real_estate.db"

api_app = FastAPI(title="Real Estate API")

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