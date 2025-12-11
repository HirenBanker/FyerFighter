import json
import os
from pathlib import Path
import secrets
import bcrypt
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(str(Path(__file__).parent.parent))

USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
USERS_FILE = os.getenv("USERS_FILE_PATH", "app/app/utils/users.json")
ENCRYPTION_MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY")

if not ENCRYPTION_MASTER_KEY:
    raise ValueError("ENCRYPTION_MASTER_KEY environment variable not set. Please set it in .env or Render environment variables.")

if USE_SUPABASE:
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        supabase = None
else:
    supabase = None

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

def load_users():
    """Load users from JSON file or Supabase."""
    if USE_SUPABASE and supabase:
        try:
            response = supabase.table("users").select("*").execute()
            users = {}
            for user in response.data:
                users[user['username']] = {
                    "password_hash": user['password_hash'],
                    "encrypted_user_key": user['encrypted_user_key'],
                    "is_admin": user['is_admin'],
                    "email": user.get('email'),
                    "phone": user.get('phone'),
                    "api_credentials": json.loads(user['api_credentials']) if user.get('api_credentials') else None,
                    "fyers_token": user.get('fyers_token')
                }
            return users
        except Exception as e:
            print(f"Error loading users from Supabase: {e}")
            return {}
    else:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}

def save_users(users):
    """Save users to JSON file or Supabase."""
    if USE_SUPABASE and supabase:
        try:
            for username, user_data in users.items():
                api_creds = json.dumps(user_data['api_credentials']) if user_data.get('api_credentials') else None
                
                existing = supabase.table("users").select("*").eq("username", username).execute()
                
                if existing.data:
                    supabase.table("users").update({
                        "password_hash": user_data['password_hash'],
                        "encrypted_user_key": user_data['encrypted_user_key'],
                        "is_admin": user_data['is_admin'],
                        "email": user_data.get('email'),
                        "phone": user_data.get('phone'),
                        "api_credentials": api_creds,
                        "fyers_token": user_data.get('fyers_token')
                    }).eq("username", username).execute()
                else:
                    supabase.table("users").insert({
                        "username": username,
                        "password_hash": user_data['password_hash'],
                        "encrypted_user_key": user_data['encrypted_user_key'],
                        "is_admin": user_data['is_admin'],
                        "email": user_data.get('email'),
                        "phone": user_data.get('phone'),
                        "api_credentials": api_creds,
                        "fyers_token": user_data.get('fyers_token')
                    }).execute()
        except Exception as e:
            print(f"Error saving users to Supabase: {e}")
    else:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)

def hash_password(password):
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(password, hashed_password):
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
    except Exception:
        return False

def create_user(username, password, is_admin=False, email=None, phone=None):
    """Create a new user"""
    users = load_users()
    if username in users:
        return False, "Username already exists"
    
    hashed_password = hash_password(password)
    user_encryption_key = generate_user_encryption_key()
    encrypted_user_key = encrypt_with_master_key(user_encryption_key)
    
    users[username] = {
        "password_hash": hashed_password,
        "encrypted_user_key": encrypted_user_key,
        "is_admin": is_admin,
        "email": email,
        "phone": phone,
        "api_credentials": None,
        "fyers_token": None
    }
    save_users(users)
    return True, "User created successfully"

def authenticate_user(username, password):
    """Authenticate a user"""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    user = users[username]
    if verify_password(password, user["password_hash"]):
        return True, "Authentication successful"
    return False, "Invalid password"

def save_api_credentials(username, api_id, api_secret):
    """Encrypt and save user's API credentials."""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    try:
        encrypted_user_key = users[username]["encrypted_user_key"]
        user_key = decrypt_with_master_key(encrypted_user_key)
        
        encrypted_api_id = encrypt_user_data(api_id, user_key)
        encrypted_api_secret = encrypt_user_data(api_secret, user_key)
        
        users[username]["api_credentials"] = {
            "api_id": encrypted_api_id,
            "api_secret": encrypted_api_secret
        }
        save_users(users)
        return True, "API credentials saved successfully."
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False, "Failed to save credentials."

def load_api_credentials(username):
    """Load and decrypt user's API credentials."""
    users = load_users()
    if username not in users:
        return None
    
    user_data = users[username]
    if not user_data.get("api_credentials"):
        return None
    
    try:
        encrypted_user_key = user_data["encrypted_user_key"]
        user_key = decrypt_with_master_key(encrypted_user_key)
        
        encrypted_api_id = user_data["api_credentials"]["api_id"]
        encrypted_api_secret = user_data["api_credentials"]["api_secret"]
        
        api_id = decrypt_user_data(encrypted_api_id, user_key)
        api_secret = decrypt_user_data(encrypted_api_secret, user_key)
        return {"api_id": api_id, "api_secret": api_secret}
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return None

def change_password(username, old_password, new_password):
    """Change user password after verifying the old password."""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    user = users[username]
    if not verify_password(old_password, user["password_hash"]):
        return False, "Current password is incorrect"
    
    hashed_password = hash_password(new_password)
    users[username]["password_hash"] = hashed_password
    save_users(users)
    return True, "Password changed successfully"

def change_email(username, new_email):
    """Update user's email address."""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    if not new_email or "@" not in new_email:
        return False, "Invalid email format"
    
    users[username]["email"] = new_email
    save_users(users)
    return True, f"Email updated to {new_email}"

def save_fyers_token(username, access_token):
    """Save user's Fyers access token."""
    users = load_users()
    if username not in users or "encrypted_user_key" not in users[username]:
        return False, "User not found or user has no encryption key."

    try:
        encrypted_user_key = users[username]["encrypted_user_key"]
        user_key = decrypt_with_master_key(encrypted_user_key)
        
        if access_token:
            encrypted_token = encrypt_user_data(access_token, user_key)
        else:
            encrypted_token = None
            
        users[username]["fyers_token"] = encrypted_token
        save_users(users)
        return True, "Token saved successfully"
    except Exception as e:
        print(f"Error encrypting or saving token: {e}")
        return False, "Failed to save token due to an encryption error."

def load_fyers_token(username):
    """Load user's Fyers access token."""
    users = load_users()
    if username not in users or "encrypted_user_key" not in users[username]:
        return None
    
    encrypted_token = users[username].get("fyers_token")
    if not encrypted_token:
        return None

    try:
        encrypted_user_key = users[username]["encrypted_user_key"]
        user_key = decrypt_with_master_key(encrypted_user_key)
        return decrypt_user_data(encrypted_token, user_key)
    except Exception as e:
        print(f"Failed to decrypt token for user {username}: {e}")
        return None

def delete_fyers_token(username):
    """Delete user's Fyers access token."""
    users = load_users()
    if username not in users:
        return False, "User not found"
    
    users[username]["fyers_token"] = None
    save_users(users)
    return True, "Token deleted successfully"
