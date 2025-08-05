import streamlit as st
import pandas as pd
import utils

st.set_page_config(page_title="Property Explorer", page_icon="🏘️", layout="wide")
st.title("🏘️ Property Explorer")
st.markdown("Use the advanced filters in the sidebar to search the entire property database.")

try:
    all_properties_df = utils.get_all_properties_df()
except Exception as e:
    st.error(f"Error loading properties: {str(e)}")
    all_properties_df = pd.DataFrame()

st.sidebar.header("Search Filters")
listing_type = st.sidebar.selectbox(
    "Listing Type:",
    options=["All"] + list(all_properties_df['listingtype'].unique()),
    index=0
)
prop_type = st.sidebar.selectbox(
    "Property Type:",
    options=["All"] + list(all_properties_df['propertytype'].unique()),
    index=0
)
locality = st.sidebar.selectbox(
    "Area / Locality:",
    options=["All"] + sorted(list(all_properties_df['arealocality'].unique())),
    index=0
)

price_col = None
if listing_type == 'Sale':
    price_col = 'askingprice'
elif listing_type == 'Rent':
    price_col = 'monthlyrent'

min_price, max_price = 0, 0
if price_col:
    valid_prices = pd.to_numeric(all_properties_df[price_col], errors='coerce').dropna()
    if not valid_prices.empty:
        min_price, max_price = int(valid_prices.min()), int(valid_prices.max())

if min_price < max_price:
    selected_price = st.sidebar.slider(
        f"Price Range (₹):",
        min_price, max_price, (min_price, max_price)
    )
else:
    selected_price = (0, 0)

st.sidebar.subheader("Filter by Amenities")
possible_amenities = [
    'Swimming Pool', 'Gymnasium', '24x7 Security', 'Clubhouse',
    'Reserved Parking', 'Power Backup', 'Elevator', 'Garden'
]
selected_amenities = st.sidebar.multiselect(
    "Select desired amenities:",
    options=possible_amenities
)

def apply_filters(df, listing_type, prop_type, locality, price_col, selected_price, selected_amenities):
    """Applies all filters to the properties DataFrame."""
    filtered_df = df.copy()
    if listing_type != "All":
        filtered_df = filtered_df[filtered_df['listingtype'] == listing_type]
    if prop_type != "All":
        filtered_df = filtered_df[filtered_df['propertytype'] == prop_type]
    if locality != "All":
        filtered_df = filtered_df[filtered_df['arealocality'] == locality]
    if selected_price[1] > 0 and price_col:
        filtered_df[price_col] = pd.to_numeric(filtered_df[price_col], errors='coerce')
        filtered_df = filtered_df.dropna(subset=[price_col])
        filtered_df = filtered_df[
            (filtered_df[price_col] >= selected_price[0]) &
            (filtered_df[price_col] <= selected_price[1])
        ]
    if selected_amenities:
        filtered_df = filtered_df[filtered_df['amenities'].apply(
            lambda x: set(selected_amenities).issubset(set(utils.extract_amenities(x)))
        )]
    return filtered_df

filtered_df = apply_filters(
    all_properties_df, listing_type, prop_type, locality,
    price_col, selected_price, selected_amenities
)

st.header("Filtered Property Listings")
st.markdown(f"Found **{len(filtered_df)}** matching properties.")
st.dataframe(filtered_df, use_container_width=True, hide_index=True)