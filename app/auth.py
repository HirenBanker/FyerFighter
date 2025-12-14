import json
import os
import bcrypt
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ENCRYPTION_MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY")

if not ENCRYPTION_MASTER_KEY:
    raise ValueError("ENCRYPTION_MASTER_KEY environment variable not set. Please set it in .env or Render environment variables.")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set.")

# Initialize clients
# Public client (anon key)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
# Admin client (service role key) - used for DB operations to bypass RLS if needed
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else None

def get_db_client():
    """Returns the best available client for DB operations."""
    return supabase_admin if supabase_admin else supabase

def generate_user_encryption_key():
    """Generates a unique encryption key for a user."""
    return Fernet.generate_key().decode()

def encrypt_with_master_key(data):
    """Encrypts data using the MASTER_KEY."""
    f = Fernet(ENCRYPTION_MASTER_KEY.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_with_master_key(encrypted_data):
    """Decrypts data using the MASTER_KEY."""
    f = Fernet(ENCRYPTION_MASTER_KEY.encode())
    return f.decrypt(encrypted_data.encode()).decode()

def encrypt_user_data(data, user_key):
    """Encrypts user data (credentials) using the user's decrypted key."""
    f = Fernet(user_key.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_user_data(encrypted_data, user_key):
    """Decrypts user data using the user's decrypted key."""
    f = Fernet(user_key.encode())
    return f.decrypt(encrypted_data.encode()).decode()

def create_user(email: str, password: str, data: dict):
    """Creates a new user in Supabase Auth and their profile."""
    try:
        # Generate and encrypt user key
        user_key = generate_user_encryption_key()
        encrypted_user_key = encrypt_with_master_key(user_key)
        
        # Add encrypted key to user metadata so it can be stored in profile
        data['encrypted_user_key'] = encrypted_user_key
        
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": data
            }
        })

        if res.user:
            # Explicitly create profile if it doesn't exist (in case trigger is missing)
            # We use the admin client if available to bypass RLS during profile creation if needed,
            # though usually the user can insert their own profile.
            client = get_db_client()
            
            # Check if profile exists
            try:
                profile_check = client.table("profiles").select("user_id").eq("user_id", res.user.id).execute()
                if not profile_check.data:
                    # Create profile manually
                    profile_data = {
                        "user_id": res.user.id,
                        "username": data.get('username'),
                        "email": email,
                        "phone": data.get('phone'),
                        "encrypted_user_key": encrypted_user_key,
                        "role": "user" # Default role
                    }
                    client.table("profiles").insert(profile_data).execute()
            except Exception as profile_error:
                print(f"Warning: Could not create profile manually: {profile_error}")
                # We don't fail the registration here, as the trigger might have worked or it might be a permission issue.
                # But if the trigger failed AND this failed, the user will have issues logging in.

            return True, "Registration successful! Please check your email to verify your account."
        else:
            return False, "Registration failed. No user object was returned by the server."
    except Exception as e:
        return False, f"An error occurred during registration: {e}"

def authenticate_user(username, password):
    """Authenticate a user"""
    try:
        # Supabase uses email to sign in. We get the user's profile to find their email from the username.
        profile = get_user_profile(username) # This can find by username or email
        if not profile:
            # If no profile is found by username, authentication will fail.
            # We could try to treat 'username' as an email, but for consistency we require username.
            return None, f"Authentication failed: User '{username}' not found."
        else:
            user_email = profile.get('email')

        res = supabase.auth.sign_in_with_password({"email": user_email, "password": password})
        return res.session, "Authentication successful"
    except Exception as e:
        return None, f"Authentication failed: {e}"

def get_user_profile(username):
    """Fetch user profile by username or email."""
    client = get_db_client()
    try:
        # Try to find by username first
        response = client.table("profiles").select("*").eq("username", username).execute()
        if response.data:
            return response.data[0]
        
        # Fallback: try to find by email
        response = client.table("profiles").select("*").eq("email", username).execute()
        if response.data:
            return response.data[0]
            
        return None
    except Exception as e:
        print(f"Error fetching profile for {username}: {e}")
        return None

def save_api_credentials(username, api_id, api_secret):
    """Encrypt and save user's API credentials."""
    profile = get_user_profile(username)
    if not profile:
        return False, "User not found"
    
    try:
        encrypted_user_key = profile.get("encrypted_user_key")
        if not encrypted_user_key:
             return False, "Encryption key not found for user."

        user_key = decrypt_with_master_key(encrypted_user_key)
        
        encrypted_api_id = encrypt_user_data(api_id, user_key)
        encrypted_api_secret = encrypt_user_data(api_secret, user_key)
        
        api_credentials = {
            "api_id": encrypted_api_id,
            "api_secret": encrypted_api_secret
        }
        
        client = get_db_client()
        # Store as JSON string to be compatible with potential text column or JSONB
        client.table("profiles").update({
            "api_credentials": json.dumps(api_credentials)
        }).eq("username", profile['username']).execute()
        
        return True, "API credentials saved successfully."
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False, "Failed to save credentials."

def load_api_credentials(username):
    """Load and decrypt user's API credentials."""
    profile = get_user_profile(username)
    if not profile:
        return None
    
    api_creds_raw = profile.get("api_credentials")
    if not api_creds_raw:
        return None
    
    try:
        # Handle both string (JSON) and dict (JSONB)
        if isinstance(api_creds_raw, str):
            api_creds = json.loads(api_creds_raw)
        else:
            api_creds = api_creds_raw

        encrypted_user_key = profile.get("encrypted_user_key")
        if not encrypted_user_key:
            return None

        user_key = decrypt_with_master_key(encrypted_user_key)
        
        encrypted_api_id = api_creds["api_id"]
        encrypted_api_secret = api_creds["api_secret"]
        
        api_id = decrypt_user_data(encrypted_api_id, user_key)
        api_secret = decrypt_user_data(encrypted_api_secret, user_key)
        return {"api_id": api_id, "api_secret": api_secret}
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return None

def change_password(username, old_password, new_password):
    """Change user password in Supabase."""
    # Note: This requires the user to be authenticated. 
    # Since we don't have the session here, this might fail if using anon key.
    # Ideally, Home.py should pass the session or we use admin key (which is dangerous for password change without verification).
    # However, Supabase Admin API allows updating user password.
    
    if supabase_admin:
        # Admin update - bypasses old password check (handled by UI or trust)
        try:
            profile = get_user_profile(username)
            if not profile:
                return False, "User not found"
            
            user_id = profile.get('user_id') # Assuming 'user_id' is in profiles
            if not user_id:
                 # Try to get user_id from auth.users? Admin can do that.
                 # But we can't easily query auth.users by username.
                 return False, "User ID not found in profile."

            supabase_admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
            return True, "Password changed successfully."
        except Exception as e:
            return False, f"Failed to change password: {e}"
    else:
        return False, "Admin client not initialized. Cannot change password."

def change_email(username, new_email):
    """Update user's email address in Supabase."""
    if not new_email or "@" not in new_email:
        return False, "Invalid email format"

    if supabase_admin:
        try:
            profile = get_user_profile(username)
            if not profile:
                return False, "User not found"
            
            user_id = profile.get('user_id')
            if not user_id:
                 return False, "User ID not found in profile."

            supabase_admin.auth.admin.update_user_by_id(user_id, {"email": new_email})
            return True, f"Email updated to {new_email}"
        except Exception as e:
            return False, f"Failed to change email: {e}"
    else:
        return False, "Admin client not initialized. Cannot change email."

def save_fyers_token(username, access_token):
    """Save user's Fyers access token."""
    profile = get_user_profile(username)
    if not profile:
        return False, "User not found"

    try:
        encrypted_user_key = profile.get("encrypted_user_key")
        if not encrypted_user_key:
            return False, "Encryption key not found."

        user_key = decrypt_with_master_key(encrypted_user_key)
        
        if access_token:
            encrypted_token = encrypt_user_data(access_token, user_key)
        else:
            encrypted_token = None
            
        client = get_db_client()
        client.table("profiles").update({
            "fyers_token": encrypted_token
        }).eq("username", profile['username']).execute()
        
        return True, "Token saved successfully"
    except Exception as e:
        print(f"Error encrypting or saving token: {e}")
        return False, "Failed to save token due to an encryption error."

def load_fyers_token(username):
    """Load user's Fyers access token."""
    profile = get_user_profile(username)
    if not profile:
        return None
    
    encrypted_token = profile.get("fyers_token")
    if not encrypted_token:
        return None

    try:
        encrypted_user_key = profile.get("encrypted_user_key")
        user_key = decrypt_with_master_key(encrypted_user_key)
        return decrypt_user_data(encrypted_token, user_key)
    except Exception as e:
        print(f"Failed to decrypt token for user {username}: {e}")
        return None

def delete_fyers_token(username):
    """Delete user's Fyers access token."""
    profile = get_user_profile(username)
    if not profile:
        return False, "User not found"
    
    try:
        client = get_db_client()
        client.table("profiles").update({
            "fyers_token": None
        }).eq("username", profile['username']).execute()
        return True, "Token deleted successfully"
    except Exception as e:
        return False, f"Failed to delete token: {e}"
