import datetime
import pandas as pd
import streamlit as st
import utils


def main():
    """Main function for the Task Manager page."""
    st.set_page_config(page_title="Task Manager", page_icon="📅", layout="wide")
    st.title("📅 My Tasks")
    st.markdown("A central place to track all your client-related tasks.")

    # --- Load Data ---
    try:
        tasks_df = utils.get_all_tasks()
    except Exception as e:
        st.error(f"Error loading tasks: {e}")
        return

    if not isinstance(tasks_df, pd.DataFrame):
        st.error("Loaded tasks data is not a DataFrame.")
        return

    # Check for expected columns
    expected_columns = ['status', 'client_name', 'client_id', 'property_id',
                        'property_locality', 'task_description', 'due_date',
                        'task_id']
    missing_columns = [col for col in expected_columns if col not in tasks_df.columns]
    if missing_columns:
        st.error(f"Missing columns in tasks data: {', '.join(missing_columns)}")
        return

    pending_tasks = tasks_df[tasks_df['status'] == 'Pending']
    completed_tasks = tasks_df[tasks_df['status'] == 'Completed']

    # --- Display Tasks ---
    st.header("Pending Tasks")
    if pending_tasks.empty:
        st.success("You're all caught up! No pending tasks.", icon="✅")
    else:
        for _, task in pending_tasks.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**Client:** {task['client_name']} ({task['client_id']})")
                    # --- NEW: Show linked property if it exists ---
                    if task['property_id']:
                        locality = task.get('property_locality', '')
                        st.markdown(f"**Property:** {task['property_id']} ({locality})")
                    st.markdown(f"> {task['task_description']}")
                with col2:
                    st.markdown(f"**Due:** {task['due_date']}")
                with col3:
                    if st.button("Mark as Complete", key=f"complete_{task['task_id']}"):
                        try:
                            utils.update_task_status(task['task_id'], "Completed")
                            st.toast("Task completed!", icon="🎉")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating task: {str(e)}")
                st.markdown("---")  # Visual separator

    with st.expander("View Completed Tasks"):
        if completed_tasks.empty:
            st.info("No tasks have been completed yet.")
        else:
            selected_columns = ['due_date', 'client_name', 'task_description']
            st.dataframe(
                completed_tasks[selected_columns],
                use_container_width=True,
                hide_index=True
            )

if __name__ == "__main__":
    main()