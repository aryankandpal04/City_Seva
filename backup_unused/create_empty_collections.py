"""
Create Empty Collections in Firebase
"""
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
for env_file in ['.env', 'cityseva.env', '.flaskenv']:
    if os.path.exists(env_file):
        print(f"Loading environment from {env_file}")
        load_dotenv(env_file)
        break

# Get Firebase config from environment
firebase_api_key = os.environ.get('FIREBASE_API_KEY')
firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID')

if not firebase_api_key or not firebase_project_id:
    print("Error: Missing Firebase configuration. Check your .env file.")
    print("Required environment variables: FIREBASE_API_KEY, FIREBASE_PROJECT_ID")
    sys.exit(1)

print(f"Using Firebase Project ID: {firebase_project_id}")

# Sign in with anonymous account to get a token
def get_token():
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
    payload = {"returnSecureToken": True}
    
    try:
        response = requests.post(auth_url, json=payload)
        response.raise_for_status()
        return response.json().get("idToken")
    except Exception as e:
        print(f"Error getting authentication token: {e}")
        return None

# Create a collection by adding a document to it
def create_collection(token, collection_name):
    api_url = f"https://firestore.googleapis.com/v1/projects/{firebase_project_id}/databases/(default)/documents/{collection_name}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # A simple document to create the collection
    document = {
        "fields": {
            "system_created": {"booleanValue": True},
            "info": {"stringValue": f"Empty collection for {collection_name}"}
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=document)
        if response.status_code in [200, 201, 202]:
            print(f"✅ Successfully created collection: {collection_name}")
            return True
        else:
            print(f"❌ Failed to create collection {collection_name}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating collection {collection_name}: {e}")
        return False

def main():
    # Get authentication token
    token = get_token()
    if not token:
        print("Failed to get authentication token")
        return
    
    # List of required collections
    collections = [
        'users',
        'categories',
        'complaints',
        'complaint_updates',
        'feedbacks',
        'audit_logs',
        'notifications',
        'official_requests',
        'complaint_media'
    ]
    
    # Create each collection
    for collection in collections:
        create_collection(token, collection)
    
    print("\nAll collections have been processed.")
    print("Please check your Firebase console to verify.")

if __name__ == "__main__":
    main() 