import pandas as pd
import streamlit as st
from datetime import date, timedelta

import assistant_engine
import utils


st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AI Assistant")
st.markdown("Chat naturally. Ask for summaries, tell it to add notes, create tasks, open client records, or fetch property details.")


@st.cache_data(show_spinner=False)
def load_data():
    clients_df = utils.get_all_clients_df()
    properties_df = utils.get_all_properties_df()
    tasks_df = utils.get_all_tasks()
    return clients_df, properties_df, tasks_df


try:
    clients_df, properties_df, tasks_df = load_data()
except Exception as exc:
    st.error(f"Unable to load assistant context: {exc}")
    st.stop()


def queue_prompt(prompt: str) -> None:
    st.session_state.assistant_pending_query = prompt


if "assistant_messages" not in st.session_state:
    st.session_state.assistant_messages = [
        {
            "role": "assistant",
            "content": (
                "I can summarize clients, recommend properties, create follow-ups, save notes, and open records. "
                "Try commands like: 'show client CL-1001', 'add note for CL-1001: call tomorrow', or 'create task for CL-1001 tomorrow: site visit'."
            ),
        }
    ]

st.sidebar.header("Assistant Context")
client_options = ["All clients"] + [f"{row['client_id']} - {row['name']}" for _, row in clients_df.iterrows()]
selected_client_label = st.sidebar.selectbox("Focus Client", client_options)
selected_client_id = None
if selected_client_label != "All clients":
    selected_client_id = selected_client_label.split(" - ")[0]

property_options = ["All properties"] + [
    f"{row['property_id']} - {row.get('propertytype', 'Property')} in {row.get('arealocality', 'Unknown')}"
    for _, row in properties_df.iterrows()
]
selected_property_label = st.sidebar.selectbox("Focus Property", property_options)
selected_property_id = None
if selected_property_label != "All properties":
    selected_property_id = selected_property_label.split(" - ")[0]

st.sidebar.caption(
    "Try: show client CL-1001 | add note for CL-1001: call tomorrow | create task for CL-1001 tomorrow: site visit"
)

if assistant_engine.is_ai_enabled():
    st.sidebar.success("AI model connected")
else:
    st.sidebar.info("Local smart-assistant mode. Set REAL_ESTATE_AI_API_KEY to enable model-backed replies.")

col1, col2, col3 = st.columns(3)
col1.metric("Clients", len(clients_df))
col2.metric("Properties", len(properties_df))
col3.metric("Pending Tasks", int((tasks_df['status'] == 'Pending').sum()) if 'status' in tasks_df.columns else 0)

st.divider()

st.subheader("Quick Prompts")
quick_col1, quick_col2, quick_col3 = st.columns(3)
quick_col1.button("Who needs follow-up today?", use_container_width=True, on_click=queue_prompt, args=("Who needs follow-up today?",))
quick_col2.button("Show the selected client", use_container_width=True, on_click=queue_prompt, args=("Show the selected client details.",))
quick_col3.button("Create a follow-up task", use_container_width=True, on_click=queue_prompt, args=("Create task for the selected client tomorrow: follow up.",))

st.caption("Command chips")
chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
chip_col1.button("show client", use_container_width=True, on_click=queue_prompt, args=("show client CL-1001",))
chip_col2.button("add note", use_container_width=True, on_click=queue_prompt, args=("add note for CL-1001: call tomorrow",))
chip_col3.button("create task", use_container_width=True, on_click=queue_prompt, args=("create task for CL-1001 tomorrow: site visit",))
chip_col4.button("market summary", use_container_width=True, on_click=queue_prompt, args=("summarize market activity",))

if st.button("Reset conversation"):
    st.session_state.assistant_messages = [st.session_state.assistant_messages[0]]
    st.session_state.pop("assistant_pending_query", None)
    st.session_state.pop("assistant_last_user_query", None)
    st.session_state.pop("assistant_last_reply", None)
    st.rerun()

st.divider()

with st.expander("Current context snapshot", expanded=False):
    context = assistant_engine.build_context(selected_client_id, selected_property_id)
    left, right = st.columns(2)
    with left:
        st.markdown("**Overview**")
        st.write(context["overview"])
        st.markdown("**Top clients**")
        if context["top_clients"]:
            st.dataframe(pd.DataFrame(context["top_clients"]), use_container_width=True, hide_index=True)
        else:
            st.info("No client summary available.")
    with right:
        st.markdown("**Pending tasks**")
        if context["pending_tasks"]:
            st.dataframe(pd.DataFrame(context["pending_tasks"]), use_container_width=True, hide_index=True)
        else:
            st.info("No pending tasks available.")

        if context.get("selected_client"):
            st.markdown("**Selected client**")
            st.write(context["selected_client"])
        if context.get("selected_property"):
            st.markdown("**Selected property**")
            st.write(context["selected_property"])

pending_prompt = st.session_state.pop("assistant_pending_query", None)
chat_prompt = st.chat_input("Ask about clients, properties, tasks, or market trends")
query = chat_prompt or pending_prompt

if query:
    st.session_state.assistant_last_user_query = query
    st.session_state.assistant_messages.append({"role": "user", "content": query})
    with st.spinner("Thinking..."):
        reply = assistant_engine.handle_chat_request(
            query,
            selected_client_id=selected_client_id,
            selected_property_id=selected_property_id,
        )
    st.session_state.assistant_messages.append({"role": "assistant", "content": reply["answer"]})
    st.session_state.assistant_last_reply = reply

    action = reply.get("action")
    if action and action.get("type") == "focus_client":
        st.session_state.home_client_jump_id = action.get("client_id")
    if action and action.get("type") == "focus_property":
        st.session_state.home_property_jump_id = action.get("property_id")

    lower_query = query.lower()
    if action and action.get("type") == "focus_client" and any(term in lower_query for term in ["show", "open", "fetch", "focus", "client details"]):
        st.session_state.home_client_jump_id = action.get("client_id")
        st.switch_page("pages/2_📈_Client_Management.py")
    if action and action.get("type") == "focus_property" and any(term in lower_query for term in ["show", "open", "fetch", "focus", "property details"]):
        st.session_state.home_property_jump_id = action.get("property_id")
        st.switch_page("pages/3_🏘️_Property_Explorer.py")

for message in st.session_state.assistant_messages:
    avatar = "🤖" if message["role"] == "assistant" else "🧑"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

last_reply = st.session_state.get("assistant_last_reply")
if last_reply:
    with st.container(border=True):
        st.markdown("**Suggested next actions**")
        if last_reply.get("suggested_actions"):
            for action in last_reply["suggested_actions"]:
                st.write(f"- {action}")
        else:
            st.write("- Ask for a summary, recommendation, or follow-up plan.")
        st.caption(f"Mode: {'AI model' if last_reply.get('used_ai') else 'local assistant'} | Intent: {last_reply.get('intent')}")

        action = last_reply.get("action")
        target_client_id = selected_client_id
        target_property_id = selected_property_id
        if action and action.get("type") == "focus_client":
            target_client_id = action.get("client_id")
        if action and action.get("type") == "focus_property":
            target_property_id = action.get("property_id")

        if action and action.get("type") == "focus_client":
            if st.button("Open client record", use_container_width=True):
                st.session_state.home_client_jump_id = action.get("client_id")
                st.switch_page("pages/2_📈_Client_Management.py")
        elif action and action.get("type") == "focus_property":
            if st.button("Open property record", use_container_width=True):
                st.session_state.home_property_jump_id = action.get("property_id")
                st.switch_page("pages/3_🏘️_Property_Explorer.py")

        st.markdown("**Do It Now**")
        quick_action_col1, quick_action_col2, quick_action_col3, quick_action_col4 = st.columns(4)

        if quick_action_col1.button("Save reply as note", use_container_width=True):
            if not target_client_id:
                st.warning("Select a client or ask the assistant to open one first.")
            else:
                try:
                    assistant_engine.save_client_note(target_client_id, last_reply.get("answer", ""))
                    st.success(f"Saved assistant reply as a note for {target_client_id}.")
                except Exception as exc:
                    st.error(f"Could not save note: {exc}")

        if quick_action_col2.button("Create follow-up", use_container_width=True):
            if not target_client_id:
                st.warning("Select a client or ask the assistant to open one first.")
            else:
                try:
                    summary_line = last_reply.get("answer", "").splitlines()[0][:120]
                    task_text = summary_line if summary_line else "Follow up based on assistant recommendation"
                    result = assistant_engine.create_follow_up_task(
                        client_id=target_client_id,
                        task_description=task_text,
                        due_date=date.today() + timedelta(days=1),
                        property_id=target_property_id,
                        task_type="Follow-up",
                        details=last_reply.get("answer", ""),
                    )
                    st.success(f"Follow-up created for {result['client_id']} due {result['due_date']}.")
                except Exception as exc:
                    st.error(f"Could not create follow-up: {exc}")

        if quick_action_col3.button("Open tasks page", use_container_width=True):
            st.switch_page("pages/5_📅_My_Tasks.py")

        if quick_action_col4.button("Fetch full client details", use_container_width=True):
            if target_client_id:
                st.session_state.assistant_pending_query = f"show client {target_client_id}"
                st.rerun()
            else:
                st.warning("Select a client first.")

st.divider()
st.subheader("Actions for the focused record")

if selected_client_id:
    action_note_default = st.session_state.get("assistant_last_user_query", "")
    action_note = st.text_area(
        "Save a note to this client",
        value=action_note_default,
        height=90,
        placeholder="Write a quick note, then save it to the communication log.",
    )
    task_description = st.text_input(
        "Create a follow-up task",
        value=f"Follow up with {selected_client_label.split(' - ', 1)[1] if ' - ' in selected_client_label else selected_client_label}",
    )
    task_due_date = st.date_input("Task due date", value=date.today() + timedelta(days=1))
    task_type = st.selectbox("Task type", ["Follow-up", "Site Visit", "Negotiation"])

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    if action_col1.button("Save note", use_container_width=True):
        try:
            assistant_engine.save_client_note(selected_client_id, action_note)
            st.success("Note saved to the client log.")
        except Exception as exc:
            st.error(f"Could not save note: {exc}")

    if action_col2.button("Create task", use_container_width=True):
        try:
            result = assistant_engine.create_follow_up_task(
                client_id=selected_client_id,
                task_description=task_description,
                due_date=task_due_date,
                property_id=selected_property_id,
                task_type=task_type,
                details=action_note if action_note else None,
            )
            st.success(f"Task created for {result['due_date']}.")
        except Exception as exc:
            st.error(f"Could not create task: {exc}")

    if action_col3.button("Open client page", use_container_width=True):
        st.session_state.home_client_jump_id = selected_client_id
        st.switch_page("pages/2_📈_Client_Management.py")

    if action_col4.button("Open property page", use_container_width=True):
        if selected_property_id:
            st.session_state.home_property_jump_id = selected_property_id
        st.switch_page("pages/3_🏘️_Property_Explorer.py")
else:
    st.info("Select a client in the sidebar to unlock note and task actions.")
