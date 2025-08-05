"""
Client Management Page for Real Estate Assistant.

This module provides interfaces for managing existing clients and adding new ones.
"""

import pandas as pd
import streamlit as st
import time
from datetime import datetime

import utils


st.set_page_config(page_title="Client Management", page_icon="📈", layout="wide")
st.title("📈 Client Relationship Management")

try:
    clients_df = utils.get_clients_with_scores()
except Exception as e:
    st.error(f"Error loading clients: {str(e)}")
    clients_df = pd.DataFrame()

tab1, tab2 = st.tabs(["**Manage Existing Clients**", "**➕ Add New Client**"])

with tab1:
    st.header("Find and Manage a Client")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    search_term = filter_col1.text_input("Search by Name, ID, or Phone:")
    status_filter = filter_col2.selectbox(
        "Filter by Status:",
        options=["All"] + sorted(clients_df['status'].unique().tolist())
    )
    looking_for_filter = filter_col3.selectbox(
        "Filter by Looking For:",
        options=["All"] + sorted(clients_df['lookingfor'].unique().tolist())
    )
    filtered_clients_df = clients_df.copy()
    if search_term:
        filtered_clients_df = filtered_clients_df[
            filtered_clients_df['name'].str.contains(search_term, case=False, na=False) |
            filtered_clients_df['client_id'].str.contains(search_term, case=False, na=False) |
            filtered_clients_df['phone'].astype(str).str.contains(search_term, case=False, na=False)
        ]
    if status_filter != "All":
        filtered_clients_df = filtered_clients_df[
            filtered_clients_df['status'] == status_filter
        ]
    if looking_for_filter != "All":
        filtered_clients_df = filtered_clients_df[
            filtered_clients_df['lookingfor'] == looking_for_filter
        ]

    st.dataframe(
        filtered_clients_df[['rating', 'name', 'status', 'lookingfor']],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="client_selection_df"
    )

    if 'client_selection_df' in st.session_state and st.session_state['client_selection_df']['selection']['rows']:
        selected_index = st.session_state['client_selection_df']['selection']['rows'][0]
        selected_client_id = filtered_clients_df.iloc[selected_index]['client_id']
        selected_client = clients_df[clients_df['client_id'] == selected_client_id].iloc[0]

        st.divider()
        st.header(f"Client Profile: {selected_client['name']}")
        st.subheader(f"Lead Score: {selected_client['rating']}")

        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.subheader("Communication Log")
            with st.form(f"note_form_{selected_client_id}"):
                new_note = st.text_area("Add a new note:")
                if st.form_submit_button("Add Note"):
                    if new_note:
                        try:
                            utils.add_communication_note(selected_client_id, new_note)
                            st.toast("Note added!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding note: {str(e)}")
            try:
                log_df = utils.get_communication_log(selected_client_id)
                st.dataframe(log_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error loading communication log: {str(e)}")
        with col2:
            st.subheader("Client Details")
            with st.expander("✏️ Edit Details"):
                with st.form(f"edit_form_{selected_client_id}"):
                    edited_data = {
                        col: st.text_input(
                            f"{col.replace('_', ' ').title()}", value=val
                        )
                        for col, val in selected_client.items()
                        if col not in ['client_id', 'score', 'rating']
                    }
                    if st.form_submit_button("Save Changes"):
                        utils.update_client_details(selected_client_id, edited_data)
                        st.toast("Details updated!")
                        time.sleep(1)
                        st.rerun()
            
            # UPGRADED: Dynamic Status Display
            latest_event = utils.get_latest_client_event(selected_client_id)
            if latest_event is not None:
                if latest_event['task_type'] == 'Site Visit':
                    st.success(
                        f"**Status:** Site visit planned for Property "
                        f"{latest_event['property_id']} on {latest_event['due_date']}."
                    )
                elif latest_event['task_type'] == 'Negotiation':
                    st.warning(
                        f"**Status:** Negotiating on Property "
                        f"{latest_event['property_id']}. Last update: {latest_event['details']}"
                    )
            else:
                st.info(f"**Status:** {selected_client['status']}")
            
            st.markdown(f"**Looking For:** {selected_client['lookingfor']}")
            st.text_area(
                "Requirements",
                value=selected_client['requirements'],
                disabled=True,
                height=100
            )
            
            st.divider()
            if st.button(
                "🗑️ Delete Client",
                type="primary",
                key=f"delete_{selected_client_id}"
            ):
                utils.delete_client_by_id(selected_client_id)
                st.success("Client deleted.")
                time.sleep(2)
                st.rerun()
    else:
        st.info("Select a client from the table above to view details.")

with tab2:
    st.header("Add a New Client")
    with st.form("add_client_form", clear_on_submit=True):
        client_name = st.text_input("Name")
        client_phone = st.text_input("Phone")
        client_email = st.text_input("Email")
        looking_for = st.selectbox("Looking For", ["Sale", "Rent"])
        requirements = st.text_area("Requirements")
        if st.form_submit_button("Submit New Client"):
            try:
                utils.add_new_client(
                    client_name, client_phone, client_email, looking_for, requirements
                )
                st.success("Client added!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding client: {str(e)}")