"""
Market Analysis Dashboard for Real Estate Assistant.

This module provides visualizations for property and client data trends.
"""

import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

import utils


# --- Page Configuration ---
st.set_page_config(page_title="Market Analysis", page_icon="📊", layout="wide")
st.title("📊 Market Intelligence Dashboard")
st.markdown("Analyze trends in your property and client data.")


@st.cache_data
def load_all_data():
    """Load properties and clients data from database."""
    properties = utils.get_all_properties_df()
    clients = utils.get_all_clients_df()
    # Convert date columns to datetime objects for calculations
    if 'listingdate' in properties.columns:
        properties['listingdate'] = pd.to_datetime(
            properties['listingdate'], errors='coerce'
        )
    return properties, clients


properties_df, clients_df = load_all_data()

st.divider()

# --- Analysis Section ---
col1, col2 = st.columns(2)

with col1:
    # --- 1. Average Price per Sq. Ft. by Locality ---
    st.subheader("📍 Avg. Price per Sq. Ft. by Locality")

    # Filter for 'Sale' properties and calculate price per sq. ft.
    if all(col in properties_df.columns for col in ['listingtype', 'askingprice', 'areasqft', 'arealocality']):
        sale_props = properties_df[properties_df['listingtype'] == 'Sale'].copy()
        # Avoid division by zero
        sale_props = sale_props[sale_props['areasqft'] > 0]
        sale_props['price_per_sqft'] = sale_props['askingprice'] / sale_props['areasqft']

        # Group by locality and get the average
        avg_price_by_locality = (
            sale_props.groupby('arealocality')['price_per_sqft']
            .mean()
            .sort_values(ascending=False)
            .dropna()
        )

        if not avg_price_by_locality.empty:
            fig = px.bar(
                avg_price_by_locality,
                x=avg_price_by_locality.index,
                y='price_per_sqft',
                title="Average Property Cost (Sale)",
                labels={
                    'price_per_sqft': 'Avg. Price per Sq. Ft. (₹)',
                    'arealocality': 'Locality'
                },
                color=avg_price_by_locality.values,
                color_continuous_scale=px.colors.sequential.Blues_r
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough sales data to calculate average prices.")
    else:
        st.error("Missing required columns in properties data.")

with col2:
    # --- 2. Client Demand Breakdown ---
    st.subheader("🤝 Client Demand by Property Size (BHK)")

    if 'requirements' in clients_df.columns:
        clients_df['req_bhk'] = (
            clients_df['requirements'].astype(str).str.extract(r'(\d+)\s*BHK')
            .fillna('Other')
        )
        bhk_demand = clients_df['req_bhk'].value_counts()

        if not bhk_demand.empty:
            fig = px.pie(
                bhk_demand,
                names=bhk_demand.index,
                values=bhk_demand.values,
                title="What Clients Are Looking For",
                hole=.3
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No client requirement data to analyze.")
    else:
        st.error("Missing 'requirements' column in clients data.")

st.divider()

# --- 3. Property "Time on Market" ---
st.subheader("⏳ Property Time on Market")

# Calculate how many days each property has been listed
if 'listingdate' in properties_df.columns:
    valid_properties = properties_df.dropna(subset=['listingdate']).copy()
    valid_properties['days_on_market'] = (
        (datetime.datetime.now() - valid_properties['listingdate']).dt.days
    )
    # Filter out negative days (future dates)
    valid_properties = valid_properties[valid_properties['days_on_market'] >= 0]

    if not valid_properties.empty:
        fig = px.histogram(
            valid_properties,
            x="days_on_market",
            nbins=20,
            title="Distribution of Listing Age",
            labels={'days_on_market': 'Days on Market'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No properties with valid listing dates to analyze.")
        # Debug info
        if not properties_df.empty:
            invalid_dates = properties_df[properties_df['listingdate'].isna()]
            example_date = (
                invalid_dates.iloc[0]['listingdate']
                if not invalid_dates.empty else 'N/A'
            )
            st.warning(
                f"Found {len(invalid_dates)} properties with invalid or missing "
                f"listing dates. Example: {example_date}"
            )
else:
    st.error("Missing 'listingdate' column in properties data.")