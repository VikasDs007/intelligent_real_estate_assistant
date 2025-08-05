import pandas as pd
import re
import sqlite3
from datetime import datetime
import os
import time
from fpdf import FPDF
from io import BytesIO
import requests

DB_FILE_PATH = "real_estate.db"
MEDIA_DIR = os.path.join("uploads", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

def initialize_database():
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS clients "
            "(client_id TEXT PRIMARY KEY, name TEXT, phone TEXT, "
            "email TEXT, lookingfor TEXT, requirements TEXT, status TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS properties "
            "(property_id TEXT PRIMARY KEY, listingstatus TEXT, listingtype TEXT, "
            "listingdate TEXT, buildingsociety TEXT, arealocality TEXT, city TEXT, "
            "pincode INTEGER, propertytype TEXT, bedroomsbhk TEXT, bathrooms INTEGER, "
            "areasqft INTEGER, areatype TEXT, floornumber INTEGER, totalfloors INTEGER, "
            "furnishing TEXT, facingdirection TEXT, parkingcars INTEGER, "
            "propertyageyrs INTEGER, amenities TEXT, askingprice REAL, monthlyrent REAL, "
            "securitydeposit REAL, maintmonth REAL, pricenegotiable TEXT, "
            "commission INTEGER, ownername TEXT, ownerphone TEXT, "
            "image_1 TEXT, image_2 TEXT, image_3 TEXT, image_4 TEXT, image_5 TEXT, "
            "image_6 TEXT, image_7 TEXT, image_8 TEXT, image_9 TEXT, image_10 TEXT, "
            "video TEXT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS communication_log "
            "(log_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, "
            "timestamp TEXT, note TEXT, "
            "FOREIGN KEY (client_id) REFERENCES clients (client_id))"
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                property_id TEXT,
                task_type TEXT, -- e.g., "Site Visit", "Negotiation", "Follow-up"
                task_description TEXT,
                due_date TEXT,
                details TEXT, -- For extra info like negotiated price
                status TEXT  -- "Pending", "Completed"
            )"""
        )
        # Add columns if they don't exist
        task_cols = [desc[1] for desc in cursor.execute("PRAGMA table_info(tasks)").fetchall()]
        if 'property_id' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN property_id TEXT")
        if 'task_type' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT")
        if 'details' not in task_cols:
            cursor.execute("ALTER TABLE tasks ADD COLUMN details TEXT")
        conn.commit()
initialize_database()

# --- HELPER FUNCTIONS (Unchanged) ---
def format_indian_currency(amount):
    """Formats the amount in Indian currency style."""
    if amount is None or not isinstance(amount, (int, float)):
        return "N/A"
    s = str(int(amount))
    if len(s) <= 3:
        return s
    # Last three digits, padded to 3 with leading zeros if needed (though unlikely)
    last_three = s[-3:]
    # Remaining digits
    remaining = s[:-3]
    # Build groups of 2 from the end
    parts = []
    i = len(remaining)
    while i > 0:
        start = max(0, i - 2)
        group = remaining[start:i]
        # Pad with leading zero only if it's not the highest group and length < 2
        if len(group) < 2 and i > 2:
            group = '0' + group
        parts.append(group)
        i = start
    # Join reversed parts (since we built from the end)
    formatted = ','.join(reversed(parts)) + ',' + last_three
    # Remove any leading comma (unlikely)
    return formatted.lstrip(',')

# --- UPGRADED: Task/Event Management Functions ---
def add_task(client_id, task_type, task_description, due_date, property_id=None, details=None):
    """Adds a new task/event and updates client status if applicable."""
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (client_id, property_id, task_type, task_description, "
                "due_date, status, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (client_id, property_id, task_type, task_description, str(due_date), "Pending", details)
            )
            if task_type in ["Site Visit", "Negotiation"]:
                new_status = "Site Visit Planned" if task_type == "Site Visit" else "Negotiating"
                cursor.execute("UPDATE clients SET status = ? WHERE client_id = ?", (new_status, client_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def get_latest_client_event(client_id):
    """Gets the most recent high-priority event to determine the client's real-time status."""
    with sqlite3.connect(DB_FILE_PATH) as conn:
        # Prioritize "Negotiation" then "Site Visit"
        query = f"""
            SELECT * FROM tasks
            WHERE client_id = '{client_id}' AND status = 'Pending' AND task_type IN ('Negotiation', 'Site Visit')
            ORDER BY due_date DESC, CASE task_type WHEN 'Negotiation' THEN 1 WHEN 'Site Visit' THEN 2 ELSE 3 END
            LIMIT 1
        """
        df = pd.read_sql(query, conn)
        return df.iloc[0] if not df.empty else None

# (All other functions from get_all_clients_df to PDF generation are unchanged and correct)
def find_budget(text):
    match = re.search(r'Budget[^\d]*([\d,]+)L?', str(text), re.IGNORECASE)
    if match: return int(match.group(1).replace(',', '')) * 100000
    match_rent = re.search(r'Rent[^\d]*([\d,]+)', str(text), re.IGNORECASE)
    if match_rent: return int(match_rent.group(1).replace(',', ''))
    return 0
def get_all_clients_df():
    with sqlite3.connect(DB_FILE_PATH) as conn: return pd.read_sql("SELECT * FROM clients", conn)
def add_new_client(name, phone, email, looking_for, requirements):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        last_id_row = cursor.execute("SELECT client_id FROM clients ORDER BY CAST(SUBSTR(client_id, 4) AS INTEGER) DESC LIMIT 1").fetchone()
        last_id = int(last_id_row[0].split('-')[1]) if last_id_row else 1000
        new_client_id = f"CL-{last_id + 1}"
        cursor.execute("INSERT INTO clients (client_id, name, phone, email, lookingfor, requirements, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (new_client_id, name, phone, email, looking_for, requirements, "New"))
        conn.commit()
def update_client_details(client_id, data):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor(); set_clause = ", ".join([f"`{key}` = ?" for key in data.keys()]); values = list(data.values()) + [client_id]
        query = f"UPDATE clients SET {set_clause} WHERE client_id = ?"; cursor.execute(query, tuple(values)); conn.commit()
def delete_client_by_id(client_id):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
        cursor.execute("DELETE FROM communication_log WHERE client_id = ?", (client_id,))
        cursor.execute("DELETE FROM tasks WHERE client_id = ?", (client_id,))
        conn.commit()
def add_communication_note(client_id, note):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor(); cursor.execute("INSERT INTO communication_log (client_id, timestamp, note) VALUES (?, ?, ?)", (client_id, timestamp, note)); conn.commit()
def get_communication_log(client_id):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        return pd.read_sql(f"SELECT timestamp, note FROM communication_log WHERE client_id = '{client_id}' ORDER BY timestamp DESC", conn)
def get_all_properties_df():
    with sqlite3.connect(DB_FILE_PATH) as conn: return pd.read_sql("SELECT * FROM properties", conn)
def save_uploaded_file(uploaded_file, property_id, media_type, index):
    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[1]; filename = f"{property_id}_{media_type}{index}{file_extension}"; file_path = os.path.join(MEDIA_DIR, filename)
        with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
        return file_path
    return None
def add_new_property(data, images, video):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        last_id_row = pd.read_sql("SELECT property_id FROM properties ORDER BY property_id DESC LIMIT 1", conn)
        if not last_id_row.empty:
            prefix, num_str = last_id_row['property_id'].iloc[0].rsplit('-', 1); new_id_num = int(num_str) + 1; new_property_id = f"{prefix}-{new_id_num}"
        else: new_property_id = "SALE-PROP-1001"
        for i in range(10):
            if i < len(images): data[f'image_{i+1}'] = save_uploaded_file(images[i], new_property_id, "img", i+1)
            else: data[f'image_{i+1}'] = None
        data['video'] = save_uploaded_file(video, new_property_id, "vid", 1)
        df = pd.DataFrame([data]); df['property_id'] = new_property_id
        df.to_sql('properties', conn, if_exists='append', index=False)
    return new_property_id
def update_property_details(property_id, data):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor(); set_clause = ", ".join([f"`{key}` = ?" for key in data.keys()]); values = list(data.values()) + [property_id]
        query = f"UPDATE properties SET {set_clause} WHERE property_id = ?"; cursor.execute(query, tuple(values)); conn.commit()
def delete_property_by_id(property_id):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor(); cursor.execute("DELETE FROM properties WHERE property_id = ?", (property_id,)); conn.commit()
def calculate_lead_score(client_row, log_counts):
    score = 0; budget = find_budget(client_row['requirements'])
    if client_row['lookingfor'] == 'Sale':
        if budget > 10000000: score += 30
        elif budget > 5000000: score += 15
    else:
        if budget > 50000: score += 30
        elif budget > 25000: score += 15
    if 'anywhere' in str(client_row['requirements']).lower(): score -= 10
    log_count = log_counts.get(client_row['client_id'], 0); score += log_count * 10
    if client_row['status'] == 'Negotiating': score += 40
    elif client_row['status'] == 'Site Visit Planned': score += 25
    if score >= 70: rating = "🔥 Hot"
    elif score >= 40: rating = "🟢 Warm"
    else: rating = "🔵 Cold"
    return score, rating
def get_clients_with_scores():
    clients_df = get_all_clients_df()
    with sqlite3.connect(DB_FILE_PATH) as conn:
        log_counts_df = pd.read_sql("SELECT client_id, COUNT(*) as count FROM communication_log GROUP BY client_id", conn)
    log_counts = log_counts_df.set_index('client_id')['count'].to_dict()
    scores_and_ratings = clients_df.apply(lambda row: calculate_lead_score(row, log_counts), axis=1)
    clients_df[['score', 'rating']] = pd.DataFrame(scores_and_ratings.tolist(), index=clients_df.index)
    return clients_df.sort_values(by='score', ascending=False)
def get_recommendations(client_id):
    client_df = get_all_clients_df().query(f"client_id == '{client_id}'"); properties_df = get_all_properties_df()
    if client_df.empty: return {"message": "Client not found.", "recommendations": []}
    client_data = client_df.iloc[0]
    req_budget = find_budget(client_data['requirements'])
    req_location_match = re.search(r'\bin\s+([\w\s]+)', str(client_data['requirements']), re.IGNORECASE)
    req_location = req_location_match.group(1).strip() if req_location_match else 'Any'
    req_bhk_match = re.search(r'(\d+)\s*BHK', str(client_data['requirements']))
    req_bhk = int(req_bhk_match.group(1)) if req_bhk_match else 0
    properties_df['bhk_numeric'] = pd.to_numeric(properties_df['bedroomsbhk'].astype(str).str.extract(r'(\d+)').iloc[:, 0], errors='coerce').fillna(0)
    price_col = 'askingprice' if client_data['lookingfor'].lower() == 'sale' else 'monthlyrent'
    properties_df['price_numeric'] = pd.to_numeric(properties_df[price_col], errors='coerce')
    base_filter = ( (properties_df['listingtype'].str.lower() == client_data['lookingfor'].lower()) & (properties_df['bhk_numeric'] >= req_bhk) )
    budget_ceiling = req_budget * 1.15
    tier1_filter = base_filter & (properties_df['price_numeric'] <= budget_ceiling)
    if req_location != 'Any': tier1_filter = tier1_filter & (properties_df['arealocality'].str.contains(req_location, case=False, na=False))
    perfect_matches = properties_df[tier1_filter]
    tier2_filter = base_filter & (properties_df['price_numeric'] <= budget_ceiling)
    good_matches = properties_df[tier2_filter]
    core_matches = properties_df[base_filter]
    final_recs = pd.concat([perfect_matches, good_matches, core_matches]).drop_duplicates(subset=['property_id']).head(10)
    if not final_recs.empty:
        if not perfect_matches.empty: message = f"Found {len(final_recs)} great matches!"
        elif not good_matches.empty: message = "No exact location matches, showing similar properties."
        else: message = "No matches in budget, showing similar properties."
    else: message = "No suitable properties found."
    response_data = { "message": message, "client_details": client_data.to_dict(), "recommendations": final_recs.to_dict(orient='records') }
    return response_data
def get_all_tasks():
    with sqlite3.connect(DB_FILE_PATH) as conn:
        query = "SELECT t.task_id, t.task_description, t.due_date, t.status, c.name as client_name, t.client_id, p.arealocality as property_locality, p.propertytype, t.property_id FROM tasks t LEFT JOIN clients c ON t.client_id = c.client_id LEFT JOIN properties p ON t.property_id = p.property_id ORDER BY t.due_date ASC"
        return pd.read_sql(query, conn)
def update_task_status(task_id, status):
    with sqlite3.connect(DB_FILE_PATH) as conn:
        cursor = conn.cursor(); cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status, task_id)); conn.commit()
# (PDF Generation code is unchanged)
class PDF(FPDF):
    def header(self): self.set_font('Arial', 'B', 15); self.cell(0, 10, 'Intelligent Real Estate Assistant', 0, 1, 'C'); self.ln(5)
    def footer(self): self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
def generate_property_report(client_details, recommendations):
    pdf = PDF(); pdf.add_page()
    def sanitize_text(text): return str(text).encode('latin-1', 'replace').decode('latin-1')
    pdf.set_font('Arial', 'B', 12); pdf.cell(0, 10, sanitize_text(f"Recommendations for: {client_details.get('name')}"), 0, 1)
    pdf.set_font('Arial', '', 10); pdf.multi_cell(0, 5, sanitize_text(f"Requirements: {client_details.get('requirements')}")); pdf.ln(10)
    image_width, text_col_width = 80, 95
    for prop in recommendations:
        pdf.set_font('Arial', 'B', 11); prop_title = f"{prop.get('bedroomsbhk', '')} {prop.get('propertytype', '')} in {prop.get('arealocality', '')}"; pdf.cell(0, 10, sanitize_text(prop_title), 0, 1, 'L')
        y_before_block = pdf.get_y()
        try:
            image_url = get_property_images(prop.get('propertytype'))[0]; response = requests.get(image_url); img = BytesIO(response.content); pdf.image(img, x=pdf.get_x(), y=y_before_block, w=image_width)
        except Exception: pdf.rect(x=pdf.get_x(), y=y_before_block, w=image_width, h=53)
        pdf.set_xy(pdf.get_x() + image_width + 5, y_before_block); pdf.set_font('Arial', '', 9); price_text = ""
        if client_details.get('lookingfor') == 'Sale' and prop.get('askingprice'): price_text = f"Asking Price: Rs. {format_indian_currency(prop.get('askingprice'))}"
        elif client_details.get('lookingfor') == 'Rent' and prop.get('monthlyrent'): price_text = f"Monthly Rent: Rs. {format_indian_currency(prop.get('monthlyrent'))} / month"
        details_text = (f"{price_text}\n" f"Area: {prop.get('areasqft'):,} sq.ft.\n" f"Furnishing: {prop.get('furnishing')}\n" f"Owner: {prop.get('ownername')} | Phone: {prop.get('ownerphone')}")
        pdf.multi_cell(text_col_width, 5, sanitize_text(details_text)); pdf.set_y(y_before_block + 53 + 10)
    return bytes(pdf.output())
def get_property_images(prop_type):
    if prop_type and isinstance(prop_type, str):
        if 'apartment' in prop_type.lower(): return ["https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg"]
        if 'bungalow' in prop_type.lower(): return ["https://images.pexels.com/photos/106399/pexels-photo-106399.jpeg"]
        if 'office' in prop_type.lower(): return ["https://images.pexels.com/photos/267507/pexels-photo-267507.jpeg"]
    return ["https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg"]