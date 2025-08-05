import pandas as pd
import plotly.express as px
import streamlit as st

import utils


# --- Page Configuration & Data Loading ---
st.set_page_config(page_title="Real Estate IA - Dashboard", page_icon="🏠", layout="wide")

try:
    clients_df = utils.get_all_clients_df()
    properties_df = utils.get_all_properties_df()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# --- Main Page UI ---
st.title("🏠 Intelligent Real Estate Dashboard")
st.markdown("Welcome to your command center. Use the sidebar to navigate.")
st.divider()

# --- Action Required: Client Follow-Ups (with Interactive Table) ---
st.header("⚡ Action Center: Client Follow-Ups")

follow_up_statuses = ["New", "Site Visit Planned", "Negotiating"]
if 'status' in clients_df.columns:
    follow_up_clients_df = clients_df[clients_df['status'].isin(follow_up_statuses)].copy()

    # Add a 'Priority' column for better visualization
    def assign_priority(status):
        if status in ["Negotiating", "Site Visit Planned"]:
            return "🔴 High"
        return "🟠 Standard"

    follow_up_clients_df['Priority'] = follow_up_clients_df['status'].apply(assign_priority)

    with st.expander(
        f"You have {len(follow_up_clients_df)} clients needing a follow-up. "
        "Click a client to take action.",
        expanded=True
    ):
        if not follow_up_clients_df.empty:
            # This makes the dataframe itself clickable
            st.dataframe(
                follow_up_clients_df[['Priority', 'name', 'status', 'phone']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="follow_up_selection"
            )

            # The action button appears below the table when a row is selected
            if ('follow_up_selection' in st.session_state and
                st.session_state['follow_up_selection']['selection']['rows']):
                selected_index = st.session_state['follow_up_selection']['selection']['rows'][0]
                selected_client = follow_up_clients_df.iloc[selected_index]

                st.info(f"Selected: **{selected_client['name']}**")
                if st.button("View Profile & Log Interaction", key=f"log_{selected_client['client_id']}"):
                    # Use the smart link to navigate to the client's full profile
                    st.session_state.selected_client_id_from_home = selected_client['client_id']
                    st.switch_page("pages/2_📈_Client_Management.py")
        else:
            st.success("Great job! No clients are currently awaiting immediate follow-up.", icon="✅")
else:
    st.error("Missing 'status' column in clients data.")

st.divider()

# --- Quick Client Search ---
st.header("🔍 Quick Client Search")
with st.form("search_form"):
    search_term = st.text_input("Search for a client by name or phone number:")
    if st.form_submit_button("Search") and search_term:
        if all(col in clients_df.columns for col in ['name', 'phone', 'status']):
            search_results = clients_df[
                clients_df['name'].str.contains(search_term, case=False, na=False) |
                clients_df['phone'].astype(str).str.contains(search_term, na=False)
            ]
            st.dataframe(
                search_results[['name', 'phone', 'status']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error("Missing required columns for search.")
st.divider()

# --- At a Glance ---
st.header("At a Glance")
total_clients = len(clients_df)
active_properties = len(properties_df)
if 'lookingfor' in clients_df.columns:
    clients_for_sale = len(clients_df[clients_df['lookingfor'] == 'Sale'])
    clients_for_rent = len(clients_df[clients_df['lookingfor'] == 'Rent'])
else:
    clients_for_sale, clients_for_rent = 0, 0
    st.warning("Missing 'lookingfor' column; client metrics may be inaccurate.")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Clients", total_clients)
col2.metric("Active Listings", active_properties)
col3.metric("Clients Buying", clients_for_sale)
col4.metric("Clients Renting", clients_for_rent)
st.divider()

# --- Visual Insights & Market Trends ---
st.header("Visual Insights & Market Trends")
map_col, chart_col = st.columns(2)
with map_col:
    st.subheader("📍 Property Locations Map")
    location_coords = {
        'Mira Road East': {'lat': 19.287, 'lon': 72.875},
        'Bhayandar East': {'lat': 19.307, 'lon': 72.861},
        'Bhayandar West': {'lat': 19.301, 'lon': 72.830},
        'Shanti Nagar': {'lat': 19.280, 'lon': 72.858},
        'Golden Nest': {'lat': 19.297, 'lon': 72.860},
        'Beverly Park': {'lat': 19.295, 'lon': 72.876},
        'Shivar Garden': {'lat': 19.290, 'lon': 72.870},
        'Jesal Park': {'lat': 19.315, 'lon': 72.858},
        'Kanakia': {'lat': 19.292, 'lon': 72.879},
    }
    if 'arealocality' in properties_df.columns:
        properties_df['lat'] = properties_df['arealocality'].map(
            lambda x: location_coords.get(x, {}).get('lat')
        )
        properties_df['lon'] = properties_df['arealocality'].map(
            lambda x: location_coords.get(x, {}).get('lon')
        )
        map_df = properties_df.dropna(subset=['lat', 'lon'])
        if not map_df.empty:
            st.map(map_df, latitude='lat', longitude='lon', size=10)
        else:
            st.info("No mappable properties.")
    else:
        st.error("Missing 'arealocality' column for mapping.")
with chart_col:
    st.subheader("📊 Property Type Distribution")
    if 'propertytype' in properties_df.columns and not properties_df.empty:
        fig = px.pie(
            properties_df,
            names='propertytype',
            title='Breakdown of Property Types',
            hole=.3,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No property type data available.")
if 'listingdate' in properties_df.columns:
    try:
        properties_df['listing_month'] = pd.to_datetime(
            properties_df['listingdate'], errors='coerce'
        ).dt.to_period('M').astype(str)
        monthly_counts = (
            properties_df.groupby('listing_month')
            .size()
            .reset_index(name='count')
            .sort_values('listing_month')
        )
        fig_line = px.line(
            monthly_counts,
            x='listing_month',
            y='count',
            title='Monthly Trend of New Listings',
            markers=True
        )
        fig_line.update_layout(
            xaxis_title='Month',
            yaxis_title='Number of New Listings'
        )
        st.plotly_chart(fig_line, use_container_width=True)
    except Exception as e:
        st.warning(f"Error processing listing dates: {e}")
else:
    st.info("No 'listingdate' column for trend analysis.")