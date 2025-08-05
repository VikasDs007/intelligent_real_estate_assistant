import streamlit as st
import pandas as pd
import utils
import time
import re
from datetime import datetime

st.set_page_config(page_title="Client Recommendations", page_icon="🤝", layout="wide")

def get_clients():
    """Fetches all clients from the database."""
    return utils.get_all_clients_df()

def get_property_images(prop_type):
    """Returns a list of image URLs based on property type."""
    if prop_type and isinstance(prop_type, str):
        if 'apartment' in prop_type.lower():
            return [
                "https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg",
                "https://images.pexels.com/photos/276724/pexels-photo-276724.jpeg",
                "https://images.pexels.com/photos/1571460/pexels-photo-1571460.jpeg"
            ]
        if 'bungalow' in prop_type.lower():
            return [
                "https://images.pexels.com/photos/106399/pexels-photo-106399.jpeg",
                "https://images.pexels.com/photos/209296/pexels-photo-209296.jpeg",
                "https://images.pexels.com/photos/259588/pexels-photo-259588.jpeg"
            ]
        if 'office' in prop_type.lower():
            return [
                "https://images.pexels.com/photos/267507/pexels-photo-267507.jpeg",
                "https://images.pexels.com/photos/1181355/pexels-photo-1181355.jpeg",
                "https://images.pexels.com/photos/7203795/pexels-photo-7203795.jpeg"
            ]
    return [
        "https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg",
        "https://images.pexels.com/photos/164558/pexels-photo-164558.jpeg",
        "https://images.pexels.com/photos/280222/pexels-photo-280222.jpeg"
    ]

st.title("🤝 Client Recommendations")

# Sidebar for client search
st.sidebar.header("Find a Client")
clients_df = get_clients()
search_term = st.sidebar.text_input("Search by Name or ID:")
if search_term:
    filtered_clients_df = clients_df[
        clients_df['name'].str.contains(search_term, case=False, na=False) |
        clients_df['client_id'].str.contains(search_term, case=False, na=False)
    ]
else:
    filtered_clients_df = clients_df
client_list = [f"{row['client_id']} - {row['name']}" for _, row in filtered_clients_df.iterrows()]
if not client_list:
    st.sidebar.warning("No clients found.")
else:
    selected_client_str = st.sidebar.selectbox("Select Client:", options=client_list)
    if selected_client_str:
        client_id = selected_client_str.split(' - ')[0]
        try:
            data = utils.get_recommendations(client_id)
            client_details = data.get("client_details", {})
            recommendations = data.get("recommendations", [])
            st.header(f"Showing Recommendations for: {client_details.get('name')}")
            if recommendations:
                pdf_bytes = utils.generate_property_report(client_details, recommendations)
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Property_Report_{client_details.get('name')}.pdf",
                    mime="application/pdf"
                )
            st.info(data.get("message"))
            st.divider()
            if not recommendations:
                st.warning("No properties to recommend.")
            else:
                for prop in recommendations:
                    prop_title = f"{prop.get('bedroomsbhk', '')} {prop.get('propertytype', '')} in {prop.get('arealocality', '')}"
                    with st.expander(prop_title, expanded=False):
                        col1, col2 = st.columns([1, 1.5])
                        with col1:
                            st.image(
                                get_property_images(prop.get('propertytype'))[0],
                                use_container_width=True,
                                caption=f"ID: {prop.get('property_id')}"
                            )
                            st.write("---")
                            st.subheader("Actions")
                            with st.form(f"visit_form_{prop.get('property_id')}"):
                                st.markdown("**Schedule a Site Visit**")
                                visit_date = st.date_input("Date", min_value=datetime.today())
                                visit_time = st.time_input("Time")
                                if st.form_submit_button("Confirm Visit", type="primary"):
                                    task_desc = f"Site visit at {prop.get('propertytype')} in {prop.get('arealocality')}"
                                    due_date = f"{visit_date} {visit_time.strftime('%H:%M')}"
                                    utils.add_task(client_id, "Site Visit", task_desc, due_date, prop.get('property_id'))
                                    st.toast("Site visit scheduled!", icon="✅")
                            with st.form(f"nego_form_{prop.get('property_id')}"):
                                st.markdown("**Start Negotiation**")
                                default_price = prop.get('askingprice') or prop.get('monthlyrent')
                                safe_default_price = 1000 if pd.isna(default_price) else int(default_price)
                                offer_price = st.number_input(
                                    "Offer Price (₹)",
                                    min_value=1000,
                                    value=safe_default_price
                                )
                                if st.form_submit_button("Log Offer"):
                                    task_desc = f"Negotiation started for {prop.get('propertytype')} in {prop.get('arealocality')}"
                                    details = f"Client offered Rs. {utils.format_indian_currency(offer_price)}"
                                    utils.add_task(
                                        client_id, "Negotiation", task_desc,
                                        datetime.now().strftime("%Y-%m-%d"),
                                        prop.get('property_id'), details
                                    )
                                    st.toast("Negotiation logged!", icon="💰")
                        with col2:
                            if client_details.get('lookingfor') == 'Sale' and prop.get('askingprice'): st.metric("Asking Price", f"₹ {utils.format_indian_currency(prop.get('askingprice'))}")
                            elif client_details.get('lookingfor') == 'Rent' and prop.get('monthlyrent'): st.metric("Monthly Rent", f"₹ {utils.format_indian_currency(prop.get('monthlyrent'))} / month")
                            st.subheader("Key Details")
                            d_col1, d_col2, d_col3 = st.columns(3); d_col1.metric("Area", f"{prop.get('areasqft', 'N/A'):,} sq.ft."); d_col2.metric("Bathrooms", prop.get('bathrooms', 'N/A')); d_col3.metric("Property Age", f"{prop.get('propertyageyrs', 'N/A')} yrs")
                            st.write("---"); st.subheader("✅ Requirement Match")
                            req_col1, prop_col1 = st.columns(2)
                            req_budget = utils.find_budget(client_details.get('requirements', ''))
                            req_bhk_match = re.search(r'(\d+)\s*BHK', str(client_details.get('requirements', ''))); req_bhk = int(req_bhk_match.group(1)) if req_bhk_match else 0
                            prop_bhk_match = re.search(r'(\d+)', str(prop.get('bedroomsbhk', ''))); prop_bhk = int(prop_bhk_match.group(1)) if prop_bhk_match else 0
                            prop_price = prop.get('askingprice') if client_details.get('lookingfor') == 'Sale' else prop.get('monthlyrent', 0)
                            bhk_match_icon = "✅" if prop_bhk >= req_bhk else "⚠️"; budget_match_icon = "✅" if prop_price is not None and prop_price <= (req_budget * 1.15) else "⚠️"
                            with req_col1: st.markdown("**Client's Request**"); st.markdown(f"- **BHK:** {req_bhk}+"); st.markdown(f"- **Budget:** Approx. ₹{utils.format_indian_currency(req_budget)}")
                            with prop_col1: st.markdown("**Property's Features**"); st.markdown(f"- {bhk_match_icon} **BHK:** {prop.get('bedroomsbhk')}"); st.markdown(f"- {budget_match_icon} **Price:** ₹{utils.format_indian_currency(prop_price)}")
                            st.write("---"); st.subheader("Photo Gallery")
                            gallery_cols = st.columns(3); images = get_property_images(prop.get('propertytype'))
                            for i, col in enumerate(gallery_cols):
                                if i < len(images): col.image(images[i], use_container_width=True)
        except Exception as e:
            st.error(f"An error occurred while fetching recommendations: {str(e)}")