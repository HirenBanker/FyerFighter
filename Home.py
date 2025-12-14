import streamlit as st
import datetime
import re
import os
import sys
import importlib
import pandas as pd
# Add the project root to the Python path BEFORE imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import auth
from common import login
from supabase import create_client, Client, PostgrestAPIError
from dotenv import load_dotenv

# Page Config
st.set_page_config(page_title="Fyer Fighter", layout="wide")

# Reduce the default top padding of the page
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None
if 'fyers_client' not in st.session_state:
    st.session_state.fyers_client = None
if 'supabase_session' not in st.session_state:
    st.session_state.supabase_session = None
if 'current_strategy' not in st.session_state:
    st.session_state.current_strategy = None
if 'fyers_token' not in st.session_state:
    st.session_state.fyers_token = None
if 'show_token_modal' not in st.session_state:
    st.session_state.show_token_modal = False
if 'regenerate_token' not in st.session_state:
    st.session_state.regenerate_token = False

# --- Supabase Initialization for Admin Functionality ---
load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_anon_key = os.environ.get("SUPABASE_KEY")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")

supabase_admin = None
if all([supabase_url, supabase_anon_key, supabase_service_key]):
    try:
        supabase_admin: Client = create_client(supabase_url, supabase_service_key)
    except Exception as e:
        # This error will only show if the admin panel is accessed with bad creds
        pass
else:
    # Admin credentials are not set. The admin panel will be disabled.
    pass

STRATEGIES = {
    "Bar Up Down": {
        "module": "barupdown.streamlit_app",
        "backtest_func": "show_backtest",
        "trade_func": "show_barupdown"
    },
    "EMA TSI": {
        "module": "ema_tsi.ui",
        "backtest_func": "show_backtest",
        "trade_func": "show_trade"
    },
    "Instant Buy": {
        "module": "instantbuy.ui",
        "backtest_func": "show_backtest",
        "trade_func": "show_trade"
    }
}

@st.cache_resource
def load_strategy_module(module_path):
    """Dynamically load a strategy module."""
    try:
        return importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError):
        return None

def get_available_strategies():
    """Get list of available strategies with their UI modules loaded."""
    available = {}
    for strategy_name, config in STRATEGIES.items():
        module = load_strategy_module(config["module"])
        if module:
            available[strategy_name] = {
                "module": module,
                "backtest_func": config["backtest_func"],
                "trade_func": config["trade_func"]
            }
    return available

def show_strategy_ui(strategy_name):
    """Dynamically display strategy UI."""
    if strategy_name not in STRATEGIES:
        st.error(f"Strategy '{strategy_name}' not found.")
        return
    
    strategy_config = STRATEGIES[strategy_name]
    module = load_strategy_module(strategy_config["module"])
    
    if not module:
        st.info(f"{strategy_name} strategy interface coming soon...")
        return
    
    backtest_func_name = strategy_config["backtest_func"]
    trade_func_name = strategy_config["trade_func"]
    
    if not (hasattr(module, backtest_func_name) and hasattr(module, trade_func_name)):
        st.info(f"{strategy_name} strategy interface coming soon...")
        return
    
    backtest_func = getattr(module, backtest_func_name)
    trade_func = getattr(module, trade_func_name)
    
    tab1, tab2 = st.tabs(["Backtest", "Trade"])
    with tab1:
        backtest_func()
    with tab2:
        trade_func()

# --- Admin Helper Functions ---
def get_user_role(user_client: Client):
    """Fetches the role of the user associated with the provided client."""
    try:
        res = user_client.rpc('get_my_role').execute()
        return res.data
    except PostgrestAPIError:
        return None

def get_all_users():
    """Fetches all user data using the secure database function."""
    if not supabase_admin: return pd.DataFrame()
    try:
        res = supabase_admin.rpc('get_all_user_data').execute()
        return pd.DataFrame(res.data)
    except PostgrestAPIError:
        return pd.DataFrame()

def delete_user(user_id: str):
    """Deletes a user from Supabase Auth."""
    if not supabase_admin: return False
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        st.success(f"Successfully deleted user {user_id}")
        return True
    except Exception as e:
        st.error(f"Failed to delete user {user_id}: {e}")
        return False

def show_admin_dashboard_ui():
    """Renders the user management interface for admins."""
    st.header("User Management")
    users_df = get_all_users()

    if users_df.empty:
        st.info("No user data found or admin client not initialized.")
        return

    st.info("You can edit the 'role' column directly. Changes are saved automatically.")
    
    users_df.set_index('user_id', inplace=True)
    users_df['delete'] = False
    
    column_config = {
        "user_id": st.column_config.TextColumn("User ID", disabled=True),
        "email": st.column_config.TextColumn("Email", disabled=True),
        "phone": st.column_config.TextColumn("Phone", disabled=True),
        "created_at": st.column_config.DatetimeColumn("Created At", format="YYYY-MM-DD HH:mm", disabled=True),
        "encrypted_credentials": st.column_config.TextColumn("Credentials", disabled=True),
        "role": st.column_config.SelectboxColumn("Role", options=["user", "admin"], required=True),
        "delete": st.column_config.CheckboxColumn("Delete User?", default=False)
    }

    edited_df = st.data_editor(
        users_df, column_config=column_config, use_container_width=True, key="user_editor"
    )

    # Handle role changes
    role_changes = edited_df[edited_df['role'] != users_df['role']]
    for user_id, row in role_changes.iterrows():
        try:
            supabase_admin.table('profiles').update({'role': row['role']}).eq('user_id', user_id).execute()
            st.toast(f"Updated role for {row['email']} to {row['role']}", icon="✅")
        except PostgrestAPIError as e:
            st.error(f"Failed to update role for {row['email']}: {e.message}")

    # Handle deletions
    users_to_delete = edited_df[edited_df['delete']]
    if not users_to_delete.empty:
        if st.button("Confirm Deletion of Selected Users", type="primary"):
            deleted_count = 0
            for user_id, row in users_to_delete.iterrows():
                if delete_user(user_id):
                    deleted_count += 1
            if deleted_count > 0:
                st.rerun()

# --- UI for the main dashboard ---
def show_dashboard():
    # --- Row 1: Title ---
    st.markdown("<h1 style='text-align: center;'>Fyer Fighter</h1>", unsafe_allow_html=True)

    # --- Row 2: User and Time ---
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.authenticated_user:
            st.write(f"Welcome, {st.session_state.authenticated_user}")
        else:
            st.markdown("[Login / Register](#user-menu)")
    with col2:
        st.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Custom horizontal rule with reduced margins
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)

    # --- Row 3: Main Content ---
    col1, col2, col3 = st.columns([1, 3, 1])

    # Column 1: Strategy List
    with col1:
        st.subheader("Strategies")
        for strategy_name in STRATEGIES.keys():
            if st.button(strategy_name):
                st.session_state.current_strategy = strategy_name

    # Column 2: Strategy GUI
    with col2:
        st.subheader("Strategy Dashboard")
        if st.session_state.current_strategy:
            show_strategy_ui(st.session_state.current_strategy)
        else:
            st.info("Please select a strategy from the left panel.")

    # Column 3: User Menu
    with col3:
        st.subheader("User Menu")
        
        if st.session_state.authenticated_user:
            # --- Admin Panel Check ---
            supabase_session = st.session_state.get("supabase_session")
            if supabase_session and supabase_url and supabase_anon_key:
                user_client = create_client(supabase_url, supabase_anon_key)
                user_client.auth.set_session(supabase_session.access_token, supabase_session.refresh_token)
                current_user_role = get_user_role(user_client)

                if current_user_role == 'admin':
                    with st.expander("🔑 Admin Dashboard", expanded=False):
                        if supabase_admin:
                            show_admin_dashboard_ui()
                        else:
                            st.error("Admin client not initialized. Check environment variables.")

            # --- Regular User Account Details ---
            with st.expander("Account Details", expanded=False):
                account_option = st.radio("Select Option:", ["Update API", "Change Password", "Change Email"], label_visibility="collapsed")
                
                if account_option == "Update API":
                    with st.form("api_form"):
                        st.write("Fyers API Credentials")
                        api_id = st.text_input("Client ID")
                        api_secret = st.text_input("Secret Key", type="password")
                        api_submitted = st.form_submit_button("Save Credentials")

                        if api_submitted:
                            if not api_id or not api_secret:
                                st.error("Both Client ID and Secret Key are required")
                            else:
                                success, message = auth.save_api_credentials(st.session_state.authenticated_user, api_id, api_secret)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                
                elif account_option == "Change Password":
                    with st.form("change_password_form"):
                        st.write("Change Password")
                        old_password = st.text_input("Current Password", type="password")
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm New Password", type="password")
                        pwd_submitted = st.form_submit_button("Change Password")
                        
                        if pwd_submitted:
                            if new_password != confirm_password:
                                st.error("New passwords do not match")
                            else:
                                success, message = auth.change_password(st.session_state.authenticated_user, old_password, new_password)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                
                elif account_option == "Change Email":
                    with st.form("change_email_form"):
                        st.write("Change Email")
                        new_email = st.text_input("New Email")
                        email_submitted = st.form_submit_button("Change Email")
                        
                        if email_submitted:
                            success, message = auth.change_email(st.session_state.authenticated_user, new_email)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
            
            if st.button("Regenerate Fyers Token"):
                st.session_state.regenerate_token = True
                st.rerun()
            
            if st.button("Logout"):
                st.session_state.authenticated_user = None
                st.session_state.fyers_client = None
                st.session_state.current_strategy = None
                st.session_state.supabase_session = None
                st.session_state.fyers_token = None
                st.session_state.regenerate_token = False
                st.session_state.show_token_modal = False
                st.rerun()
        else:
            with st.expander("Login / Register", expanded=True):
                tab1, tab2 = st.tabs(["Login", "Register"])
                
                with tab1:
                    with st.form("login_form"):
                        login_email = st.text_input("Email")
                        login_password = st.text_input("Password", type="password")
                        login_submitted = st.form_submit_button("Login")
                        
                        if login_submitted:
                            session, message = auth.authenticate_user(login_email, login_password)
                            if session:
                                # After successful login, get the user's profile to display their username
                                user_profile = supabase_admin.table('profiles').select('username').eq('user_id', session.user.id).single().execute()
                                if user_profile.data:
                                    st.session_state.authenticated_user = user_profile.data.get('username', login_email)
                                else:
                                    # Fallback to email if profile is not found for some reason
                                    st.session_state.authenticated_user = login_email
                                # Store the Supabase session object
                                st.session_state.supabase_session = session
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error(message)
                
                with tab2:
                    with st.form("register_form"):
                        reg_username = st.text_input("Username")
                        reg_email = st.text_input("Email")
                        reg_phone = st.text_input("Phone Number")
                        reg_password = st.text_input("Password", type="password")
                        reg_confirm_password = st.text_input("Confirm Password", type="password")
                        reg_submitted = st.form_submit_button("Register")
                        
                        if reg_submitted:
                            if reg_password != reg_confirm_password:
                                st.error("Passwords do not match")
                            else:
                                # The username and phone are metadata for the user profile
                                user_metadata = {
                                    'username': reg_username,
                                    'phone': reg_phone
                                }
                                success, message = auth.create_user(reg_email, reg_password, data=user_metadata)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
            
    # Custom horizontal rule with reduced margins
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)

    # --- Row 4: Announcements ---
    st.subheader("Announcements")
    st.info("This is a placeholder for announcements and advertisements.")

# --- Fyers Token Modals and Initialization ---

@st.dialog("Generate Fyers Token")
def show_token_generation_dialog(client_id, secret_key):
    """Displays a dialog for the Fyers token generation process."""
    auth_url = login.generate_authcode_url(client_id, secret_key)
    st.info("Please log in to Fyers to generate an auth code.")
    st.markdown(f"[Click here to log in]({auth_url})", unsafe_allow_html=True)

    redirected_url = st.text_input("Paste the full redirected URL here:")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Generate"):
            if redirected_url:
                match = re.search(r'auth_code=([^&]+)', redirected_url)
                if match:
                    auth_code = match.group(1)
                    with st.spinner("Generating access token..."):
                        access_token = login.generate_access_token(auth_code, client_id, secret_key)
                    
                    if access_token:
                        st.session_state.fyers_token = access_token
                        auth.save_fyers_token(st.session_state.authenticated_user, access_token)
                        st.session_state.regenerate_token = False
                        # Upon success, clear the old client to force re-initialization
                        st.session_state.fyers_client = None 
                        st.success("Successfully generated and saved access token!")
                        st.rerun()
                    else:
                        st.error("Failed to generate access token from auth_code.")
                else:
                    st.error("Could not find 'auth_code' in the provided URL. Please paste the full URL.")
            else:
                st.warning("Please paste the redirected URL before generating.")
    with col2:
        if st.button("Cancel"):
            st.session_state.regenerate_token = False
            st.rerun()


@st.dialog("Fyers Token")
def show_token_modal():
    """Asks the user whether to use an existing token or generate a new one."""
    st.write("You have an existing Fyers token. Do you want to use it or generate a new one?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Use Existing Token"):
            st.session_state.fyers_token = auth.load_fyers_token(st.session_state.authenticated_user)
            st.session_state.show_token_modal = False
            st.session_state.regenerate_token = False
            st.rerun()
    with col2:
        if st.button("Generate New Token"):
            st.session_state.regenerate_token = True
            st.session_state.show_token_modal = False
            st.rerun()

def initialize_fyers_client():
    """Initializes the Fyers client if a token is available in the session state."""
    if not st.session_state.fyers_token:
        return

    credentials = auth.load_api_credentials(st.session_state.authenticated_user)
    if not credentials:
        return 

    client_id = credentials['api_id']
    fyers = login.initialize_fyers_client(client_id, st.session_state.fyers_token)
    
    if fyers:
        st.session_state.fyers_client = fyers
        st.success("Fyers client initialized successfully!")
    else:
        # Token is likely expired or invalid, so clear it and force regeneration.
        st.session_state.fyers_token = None
        st.session_state.fyers_client = None
        auth.save_fyers_token(st.session_state.authenticated_user, None)
        st.session_state.regenerate_token = True
        st.warning("Fyers client initialization failed. Your token may be expired.")
        st.rerun()

# --- Main App Logic ---

if st.session_state.authenticated_user:
    # Priority 1: Handle an explicit request to regenerate the token.
    # This runs regardless of whether a client exists, allowing regeneration at any time.
    if st.session_state.get("regenerate_token"):
        credentials = auth.load_api_credentials(st.session_state.authenticated_user)
        if not credentials:
            st.warning("Please enter your Fyers API credentials in the 'Account Details' section.")
            st.session_state.regenerate_token = False # Reset flag, can't proceed.
        else:
            show_token_generation_dialog(credentials['api_id'], credentials['api_secret'])
    
    # Priority 2: If not regenerating, and no client exists, run the initial setup.
    elif not st.session_state.fyers_client:
        credentials = auth.load_api_credentials(st.session_state.authenticated_user)
        stored_token = auth.load_fyers_token(st.session_state.authenticated_user)

        if not credentials:
            st.warning("Please enter your Fyers API credentials in the 'Account Details' section.")
        
        elif not st.session_state.fyers_token and stored_token:
            show_token_modal()
        
        elif not st.session_state.fyers_token and not stored_token:
            st.session_state.regenerate_token = True
            st.rerun()

        elif st.session_state.fyers_token:
            initialize_fyers_client()

show_dashboard()
