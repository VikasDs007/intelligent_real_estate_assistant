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

focused_property_id = st.session_state.get("home_property_jump_id")

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

if focused_property_id and focused_property_id not in filtered_df['property_id'].values:
    focused_row = all_properties_df[all_properties_df['property_id'] == focused_property_id]
    if not focused_row.empty:
        filtered_df = pd.concat([focused_row, filtered_df], ignore_index=True)

st.header("Filtered Property Listings")
st.markdown(f"Found **{len(filtered_df)}** matching properties.")
st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="property_selection_df"
)

selected_property = None
if 'property_selection_df' in st.session_state and st.session_state['property_selection_df']['selection']['rows']:
    selected_index = st.session_state['property_selection_df']['selection']['rows'][0]
    selected_property = filtered_df.iloc[selected_index]
elif focused_property_id and focused_property_id in all_properties_df['property_id'].values:
    selected_property = all_properties_df[all_properties_df['property_id'] == focused_property_id].iloc[0]

if selected_property is not None:
    if focused_property_id == selected_property['property_id']:
        st.info("Opened from Quick Jump. This property is shown for quick review.")

    st.subheader("Property Details")
    detail_col1, detail_col2 = st.columns([1.2, 1])
    with detail_col1:
        st.markdown(f"**{selected_property.get('propertytype', 'Property')}** in **{selected_property.get('arealocality', 'Unknown')}**")
        st.markdown(f"**Listing Type:** {selected_property.get('listingtype', 'N/A')}")
        st.markdown(f"**Status:** {selected_property.get('listingstatus', 'N/A')}")
        if selected_property.get('askingprice'):
            st.markdown(f"**Asking Price:** ₹{int(float(selected_property.get('askingprice'))):,}")
        if selected_property.get('monthlyrent'):
            st.markdown(f"**Monthly Rent:** ₹{int(float(selected_property.get('monthlyrent'))):,}")
        if selected_property.get('areasqft'):
            st.markdown(f"**Area:** {selected_property.get('areasqft')} sq.ft.")
    with detail_col2:
        st.markdown("**Amenities**")
        amenities = utils.extract_amenities(selected_property.get('amenities'))
        if amenities:
            st.write(", ".join(amenities))
        else:
            st.write("No amenities listed.")