import streamlit as st
import pandas as pd
import utils
import time
from datetime import datetime
import os


"""
Property Management Page

This script handles adding, editing, and deleting property listings
with media upload capabilities.
"""


st.set_page_config(page_title="Property Management", page_icon="🏢", layout="wide")
st.title("🏢 Property Management")

tab1, tab2 = st.tabs(["**➕ Add New Property**", "**✏️ Edit / Delete Property**"])

with tab1:
    st.header("Add a New Property Listing")
    with st.form("add_property_form", clear_on_submit=False):
        # (The form fields are the same)
        st.subheader("Core Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            listing_type = st.selectbox("Listing Type", ["Sale", "Rent"])
            property_type = st.selectbox("Property Type",
                                         ["Apartment", "Bungalow",
                                          "Office Space", "Shop", "Plot"])
            bedrooms_bhk = st.selectbox("Bedrooms (BHK)",
                                        ["1 BHK", "2 BHK", "3 BHK",
                                         "4 BHK", "5+ BHK", "N/A"])
        with col2:
            building_society = st.text_input("Building / Society Name")
            area_locality = st.text_input("Area / Locality",
                                          "Mira Road East")
            city = st.text_input("City", "Mira Bhayandar")
        with col3:
            pincode = st.number_input("Pincode", value=401107, step=1)
            listing_date = st.date_input("Listing Date", datetime.now())
        st.divider()
        st.subheader("Property Specifications")
        spec_col1, spec_col2, spec_col3 = st.columns(3)
        with spec_col1:
            areasqft = st.number_input("Area (Sq. Ft.)", 100, 10000, 1000, 50)
            bathrooms = st.number_input("Bathrooms", 1, 10, 2)
            furnishing = st.selectbox("Furnishing",
                                      ["Fully Furnished",
                                       "Semi-Furnished", "Unfurnished"])
        with spec_col2:
            floornumber = st.number_input("Floor Number", 0, 50, 5)
            totalfloors = st.number_input("Total Floors", 0, 50, 15)
            facingdirection = st.selectbox("Facing Direction",
                                           ["East", "West", "North",
                                            "South", "North-East",
                                            "North-West", "South-East",
                                            "South-West"])
        with spec_col3:
            parkingcars = st.number_input("Car Parking", 0, 10, 1)
            propertyageyrs = st.number_input("Property Age (Years)",
                                             0, 100, 5)
        amenities = st.text_area("Amenities (comma-separated)",
                                 "24x7 Security, Elevator, Power Backup")
        st.divider()
        st.subheader("Pricing & Ownership")
        price_col1, price_col2, owner_col = st.columns(3)
        with price_col1:
            if listing_type == "Sale":
                askingprice = st.number_input("Asking Price (₹)",
                                              min_value=0, value=5000000,
                                              step=100000)
                monthlyrent, securitydeposit = None, None
            else:
                monthlyrent = st.number_input("Monthly Rent (₹)",
                                              min_value=0, value=25000,
                                              step=1000)
                securitydeposit = st.number_input("Security Deposit (₹)",
                                                  min_value=0, value=100000,
                                                  step=10000)
                askingprice = None
        with price_col2:
            maintmonth = st.number_input("Maintenance / Month (₹)",
                                         min_value=0, value=2000, step=100)
            pricenegotiable = st.selectbox("Price Negotiable?",
                                           ["Yes", "Slightly", "No"])
            commission = st.number_input("Commission (%)", 1, 10, 2)
        with owner_col:
            ownername = st.text_input("Owner Name")
            ownerphone = st.text_input("Owner Phone")
        
        # --- UPGRADED: File Uploaders for 10 images ---
        st.divider()
        st.subheader("Upload Media")
        uploaded_images = st.file_uploader("Upload Photos (up to 10)",
                                           type=['jpg', 'jpeg', 'png'],
                                           accept_multiple_files=True)
        uploaded_video = st.file_uploader("Upload a Video Tour",
                                          type=['mp4', 'mov', 'avi'])

        if st.form_submit_button("Submit New Property", type="primary"):
            if len(uploaded_images) > 10:
                st.error("You can upload a maximum of 10 images.")
            else:
                data = { 'listingtype': listing_type, 'propertytype': property_type, 'bedroomsbhk': bedrooms_bhk,'buildingsociety': building_society, 'arealocality': area_locality, 'city': city,'pincode': pincode, 'listingdate': str(listing_date), 'areasqft': areasqft,'bathrooms': bathrooms, 'furnishing': furnishing, 'floornumber': floornumber,'totalfloors': totalfloors, 'facingdirection': facingdirection, 'parkingcars': parkingcars,'propertyageyrs': propertyageyrs, 'amenities': amenities, 'askingprice': askingprice,'monthlyrent': monthlyrent, 'securitydeposit': securitydeposit, 'maintmonth': maintmonth,'pricenegotiable': pricenegotiable, 'commission': commission, 'ownername': ownername,'ownerphone': ownerphone, 'listingstatus': 'Available'}
                try:
                    utils.add_new_property(data, uploaded_images, uploaded_video)
                    st.success("Property and its media have been added successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding property: {str(e)}")

with tab2:
    st.header("Edit or Delete an Existing Listing")
    try:
        properties_df = utils.get_all_properties_df()
    except Exception as e:
        st.error(f"Error loading properties: {str(e)}")
        properties_df = pd.DataFrame()
    # (Search and filter logic is unchanged)
    search_prop = st.text_input("Search by ID, Type, or Locality:",
                                key="prop_search")
    if search_prop:
        filtered_props_df = properties_df[properties_df['property_id'].str.contains(search_prop, case=False, na=False) | properties_df['arealocality'].str.contains(search_prop, case=False, na=False) | properties_df['propertytype'].str.contains(search_prop, case=False, na=False)]
    else:
        filtered_props_df = properties_df
    
    st.dataframe(filtered_props_df, use_container_width=True,
                 hide_index=True, on_select="rerun",
                 selection_mode="single-row", key="prop_selection_df")

    if 'prop_selection_df' in st.session_state and st.session_state['prop_selection_df']['selection']['rows']:
        selected_index = st.session_state['prop_selection_df']['selection']['rows'][0]
        selected_prop = filtered_props_df.iloc[selected_index]
        property_id = selected_prop['property_id']

        st.divider()
        st.header(f"Editing Property: {property_id}")
        
        # --- UPGRADED: Display up to 10 images ---
        st.subheader("Current Media")
        # Use a flexible grid for images
        img_cols = st.columns(5) 
        img_index = 0
        for i in range(1, 11):
            img_path = selected_prop.get(f'image_{i}')
            if img_path and os.path.exists(img_path):
                img_cols[img_index % 5].image(img_path,
                                              caption=f"Image {i}",
                                              use_column_width=True)
                img_index += 1
        
        vid_path = selected_prop.get('video')
        if vid_path and os.path.exists(vid_path):
            st.video(vid_path)

        with st.form(f"edit_prop_form_{property_id}"):
            st.subheader("Update Details")
            # (Edit form is unchanged)
            edited_data = {col: st.text_input(f"{col.replace('_', ' ').title()}",
                                              value=val)
                           for col, val in selected_prop.items()
                           if col not in ['property_id', 'display']}
            save_button, delete_button = st.columns(2)
            if save_button.form_submit_button("💾 Save Changes"):
                try:
                    utils.update_property_details(property_id, edited_data)
                    st.toast("Property updated!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating property: {str(e)}")
            if delete_button.form_submit_button("🗑️ Delete Property",
                                                type="primary"):
                try:
                    utils.delete_property_by_id(property_id)
                    st.success("Property deleted.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting property: {str(e)}")