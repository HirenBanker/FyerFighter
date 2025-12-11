# login.py
import re
from fyers_apiv3 import fyersModel
from common.config import REDIRECT_URI, GRANT_TYPE, RESPONSE_TYPE, STATE

def generate_authcode_url(client_id, secret_key):
    """Generate the Fyers authentication URL."""
    appSession = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=REDIRECT_URI,
        response_type=RESPONSE_TYPE,
        state=STATE,
        secret_key=secret_key,
        grant_type=GRANT_TYPE
    )
    return appSession.generate_authcode()

def generate_access_token(auth_code, client_id, secret_key):
    """Generate an access token from the auth code."""
    try:
        appSession = fyersModel.SessionModel(
            client_id=client_id,
            redirect_uri=REDIRECT_URI,
            response_type=RESPONSE_TYPE,
            state=STATE,
            secret_key=secret_key,
            grant_type=GRANT_TYPE
        )
        appSession.set_token(auth_code)
        response = appSession.generate_token()
        if "access_token" in response:
            return response["access_token"]
        else:
            print("Error generating access token:", response)
            return None
    except Exception as e:
        print("Error generating access token:", e)
        return None

def initialize_fyers_client(client_id, token):
    """Initialize the FyersModel with a client_id and token."""
    if not client_id or not token:
        return None

    fyers = fyersModel.FyersModel(
        client_id=client_id,
        token=token,
        is_async=False,
        log_path=""
    )
    
    profile = fyers.get_profile()
    if profile and profile.get('s') == 'ok':
        return fyers
    else:
        print("Invalid token or client_id.")
        return None
