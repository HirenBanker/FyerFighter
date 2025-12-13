import streamlit as st
import datetime
import re
import os
import sys
# Add the project root to the Python path BEFORE imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import auth
from common import login
import importlib

# Page Config
st.set_page_config(page_title="Fyer Fighter", layout="wide")

# Initialize session state
if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None
if 'fyers_client' not in st.session_state:
    st.session_state.fyers_client = None
if 'current_strategy' not in st.session_state:
    st.session_state.current_strategy = None
if 'fyers_token' not in st.session_state:
    st.session_state.fyers_token = None
if 'show_token_modal' not in st.session_state:
    st.session_state.show_token_modal = False
if 'regenerate_token' not in st.session_state:
    st.session_state.regenerate_token = False

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

# --- UI for the main dashboard ---
def show_dashboard():
    # --- Row 1: Title ---
    st.title("Fyer Fighter")

    # --- Row 2: User and Time ---
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.authenticated_user:
            st.write(f"Welcome, {st.session_state.authenticated_user}")
        else:
            st.markdown("[Login / Register](#user-menu)")
    with col2:
        st.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    st.markdown("---")

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
                st.session_state.fyers_token = None
                st.session_state.regenerate_token = False
                st.session_state.show_token_modal = False
                st.rerun()
        else:
            with st.expander("Login / Register", expanded=True):
                tab1, tab2 = st.tabs(["Login", "Register"])
                
                with tab1:
                    with st.form("login_form"):
                        login_username = st.text_input("Username")
                        login_password = st.text_input("Password", type="password")
                        login_submitted = st.form_submit_button("Login")
                        
                        if login_submitted:
                            success, message = auth.authenticate_user(login_username, login_password)
                            if success:
                                st.session_state.authenticated_user = login_username
                                st.success(message)
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
                                success, message = auth.create_user(reg_username, reg_password, email=reg_email, phone=reg_phone)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
            
    st.markdown("---")

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
