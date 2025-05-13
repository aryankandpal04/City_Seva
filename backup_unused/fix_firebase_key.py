"""
Fix Firebase Service Account Key Issues
"""
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
env_files = ['.env', 'cityseva.env', '.flaskenv']
env_loaded = False

for env_file in env_files:
    if os.path.exists(env_file):
        print(f"Loading environment from {env_file}")
        load_dotenv(env_file)
        env_loaded = True
        break

if not env_loaded:
    print("Warning: No environment file found")

# Check Firebase configuration
firebase_key_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
print(f"Current FIREBASE_SERVICE_ACCOUNT_KEY: {firebase_key_path}")

def validate_key_file(key_path):
    """Validate that the service account key file exists and has valid format"""
    if not key_path:
        return False, "No key path specified in environment"
    
    # Check if it's a JSON string
    if key_path.startswith('{'):
        try:
            key_data = json.loads(key_path)
            print("Service account key is provided as a JSON string")
            return check_key_content(key_data)
        except json.JSONDecodeError:
            return False, "Invalid JSON string in environment variable"
    
    # It's a file path
    if not os.path.exists(key_path):
        return False, f"Service account key file not found at: {key_path}"
    
    try:
        with open(key_path, 'r') as f:
            key_data = json.load(f)
        return check_key_content(key_data)
    except Exception as e:
        return False, f"Error reading service account key file: {e}"

def check_key_content(key_data):
    """Check that key data has required fields"""
    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
    
    for field in required_fields:
        if field not in key_data:
            return False, f"Missing required field in service account key: {field}"
    
    # Check for known issues
    if key_data.get('type') != 'service_account':
        return False, "Invalid key type, must be 'service_account'"
    
    # Check private key format
    if not key_data.get('private_key', '').startswith('-----BEGIN PRIVATE KEY-----'):
        return False, "Invalid private key format"
    
    return True, "Service account key is valid"

def backup_env_file(env_file):
    """Create a backup of the environment file"""
    if not os.path.exists(env_file):
        return False
    
    backup_file = f"{env_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(env_file, 'r') as src, open(backup_file, 'w') as dst:
            dst.write(src.read())
        print(f"Created backup of {env_file} at {backup_file}")
        return True
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return False

def update_env_file(env_file, key_path):
    """Update the environment file with the new key path"""
    if not os.path.exists(env_file):
        print(f"Environment file {env_file} not found")
        return False
    
    # Backup the file first
    if not backup_env_file(env_file):
        return False
    
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Find and replace the FIREBASE_SERVICE_ACCOUNT_KEY line
        key_updated = False
        for i, line in enumerate(lines):
            if line.startswith('FIREBASE_SERVICE_ACCOUNT_KEY='):
                lines[i] = f'FIREBASE_SERVICE_ACCOUNT_KEY={key_path}\n'
                key_updated = True
                break
        
        # If not found, add it at the end
        if not key_updated:
            lines.append(f'FIREBASE_SERVICE_ACCOUNT_KEY={key_path}\n')
        
        # Write the updated file
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print(f"Updated {env_file} with new service account key path")
        return True
    except Exception as e:
        print(f"Failed to update environment file: {e}")
        return False

if firebase_key_path:
    valid, message = validate_key_file(firebase_key_path)
    print(f"Key validation result: {message}")
    
    if not valid:
        print("\nYour Firebase service account key is invalid or corrupted.")
        print("Here's how to fix it:")
        print("\n1. Go to Firebase Console: https://console.firebase.google.com/")
        print("2. Select your project")
        print("3. Click the gear icon (⚙️) for Project Settings")
        print("4. Go to the 'Service accounts' tab")
        print("5. Click 'Generate new private key' button")
        print("6. Save the downloaded JSON file to your project directory")
        print("\nAfter downloading the new key, update your environment file with the new path:")
        print("   FIREBASE_SERVICE_ACCOUNT_KEY=path/to/your-new-key.json")
        
        # Check if we can find cityseva.env for potential update
        env_to_update = None
        for env_file in env_files:
            if os.path.exists(env_file):
                env_to_update = env_file
                break
        
        if env_to_update:
            print(f"\nDetected environment file: {env_to_update}")
            if input(f"Do you want to update {env_to_update} with a new key path? (y/n): ").lower() == 'y':
                new_key_path = input("Enter the path to your new service account key file: ")
                if os.path.exists(new_key_path):
                    update_env_file(env_to_update, new_key_path)
                    print("\nEnvironment file updated successfully!")
                    print("Try running your app again.")
                else:
                    print(f"Error: File not found at {new_key_path}")
else:
    print("No Firebase service account key configured in environment variables")
    print("Please set FIREBASE_SERVICE_ACCOUNT_KEY in your environment file") 