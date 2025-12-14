import os
import streamlit as st
import sys

# Add the project root to the Python path to allow imports from `app`
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
from supabase import create_client, Client, PostgrestAPIError
from dotenv import load_dotenv

# --- 1. INITIALIZATION ---
# Load environment variables for local development
load_dotenv()

# Initialize two Supabase clients:
# 1. A user-level client to check the current user's role.
# 2. An admin-level client (using the service key) for performing admin actions.
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_KEY") # The public anon key
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY") # The admin service role key

    if not all([supabase_url, supabase_anon_key, supabase_service_key]):
        st.error("Supabase credentials are not set in environment variables.")
        st.stop()

    # Admin client for performing privileged operations
    supabase_admin: Client = create_client(supabase_url, supabase_service_key)

except Exception as e:
    st.error(f"Error initializing Supabase client: {e}")
    st.stop()

# --- 2. HELPER FUNCTIONS ---
def get_user_role(user_client: Client):
    """Fetches the role of the user associated with the provided client."""
    try:
        res = user_client.rpc('get_my_role').execute()
        return res.data
    except PostgrestAPIError as e:
        st.error(f"Error fetching user role: {e.message}")
        return None

def get_all_users():
    """Fetches all user data using the secure database function."""
    try:
        res = supabase_admin.rpc('get_all_user_data').execute()
        return pd.DataFrame(res.data)
    except PostgrestAPIError as e:
        st.error(f"Error fetching users: {e.message}")
        return pd.DataFrame()

def delete_user(user_id: str):
    """Deletes a user from Supabase Auth."""
    try:
        # Use the admin client to delete a user
        supabase_admin.auth.admin.delete_user(user_id)
        st.success(f"Successfully deleted user {user_id}")
        return True
    except Exception as e:
        st.error(f"Failed to delete user {user_id}: {e}")
        return False

# --- 3. ADMIN DASHBOARD UI ---
st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("🔑 Admin Dashboard")

# --- SECURITY CHECK ---
# This page is only accessible to logged-in users.
if not st.session_state.get("authenticated_user"):
    st.error("You must be logged in to view this page.")
    st.warning("Please log in from the Home page.")
    st.stop()

# Check if the logged-in user has the 'admin' role.
# We create a temporary client authenticated as the user to check their role.
supabase_session = st.session_state.get("supabase_session")
user_client = create_client(supabase_url, supabase_anon_key)
if supabase_session:
    # Restore the user's session into a temporary client
    user_client.auth.set_session(supabase_session.access_token, supabase_session.refresh_token)

current_user_role = get_user_role(user_client)

if current_user_role == 'admin':
    st.success(f"Admin access granted. Welcome, {st.session_state.authenticated_user}!")

    # --- DATA DISPLAY AND MANAGEMENT ---
    st.header("User Management")

    # Fetch and display users
    users_df = get_all_users()

    if users_df.empty:
        st.info("No user data found.")
    else:
        st.info("You can edit the 'role' column directly. Changes are saved automatically.")
        
        users_df.set_index('user_id', inplace=True)
        users_df['delete'] = False
        
        column_config = {
            "user_id": st.column_config.TextColumn("User ID", disabled=True),
            "email": st.column_config.TextColumn("Email", disabled=True),
            "phone": st.column_config.TextColumn("Phone", disabled=True),
            "created_at": st.column_config.DatetimeColumn("Created At", format="YYYY-MM-DD HH:mm", disabled=True),
            "encrypted_credentials": st.column_config.TextColumn("Credentials", disabled=True),
            "role": st.column_config.SelectboxColumn(
                "Role",
                options=["user", "admin"],
                required=True,
            ),
            "delete": st.column_config.CheckboxColumn("Delete User?", default=False)
        }

        edited_df = st.data_editor(
            users_df,
            column_config=column_config,
            use_container_width=True,
            key="user_editor"
        )

        # --- 4. HANDLE CHANGES ---
        role_changes = edited_df[edited_df['role'] != users_df['role']]
        for user_id, row in role_changes.iterrows():
            try:
                supabase_admin.table('profiles').update({'role': row['role']}).eq('user_id', user_id).execute()
                st.toast(f"Updated role for {row['email']} to {row['role']}", icon="✅")
            except PostgrestAPIError as e:
                st.error(f"Failed to update role for {row['email']}: {e.message}")

        users_to_delete = edited_df[edited_df['delete']]
        if not users_to_delete.empty:
            if st.button("Confirm Deletion of Selected Users", type="primary"):
                deleted_count = 0
                for user_id, row in users_to_delete.iterrows():
                    if delete_user(user_id):
                        deleted_count += 1
                if deleted_count > 0:
                    st.rerun()
else:
    st.error("You do not have permission to view this page.")
    st.warning("Please log in with an admin account on the Home page.")
