"""
Force Create Collections - Directly creates all required collections in Firebase
"""
import os
import sys
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Get the path to the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

def create_collections():
    """Create all required collections in Firebase by adding a document to each collection"""
    
    print("Starting Firebase collection creation...")

    # Try to load environment variables from different possible files
    for env_file in ['.env', 'cityseva.env', '.flaskenv']:
        env_path = os.path.join(project_root, env_file)
        if os.path.exists(env_path):
            print(f"Loading environment from {env_file}")
            load_dotenv(env_path)
            break

    # Try to get the service account key from environment variable
    service_account_key_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    service_account_json = None
    
    if service_account_key_path:
        print(f"Found FIREBASE_SERVICE_ACCOUNT_KEY: {service_account_key_path}")
        
        # Check if it's a file path or a JSON string
        if service_account_key_path.startswith('{'):
            print("Using service account JSON from environment variable")
            try:
                service_account_json = json.loads(service_account_key_path)
            except json.JSONDecodeError as e:
                print(f"Error parsing service account JSON: {e}")
                return False
        else:
            # Try to load from file path
            svc_path = os.path.join(project_root, service_account_key_path)
            if os.path.exists(svc_path):
                print(f"Using service account file from: {svc_path}")
                try:
                    with open(svc_path, 'r') as f:
                        service_account_json = json.load(f)
                except Exception as e:
                    print(f"Error reading service account file: {e}")
                    return False
            else:
                print(f"Service account file not found at: {svc_path}")
    
    # If not found in environment, try default location
    if service_account_json is None:
        default_path = os.path.join(project_root, "firebase-service-account.json")
        if os.path.exists(default_path):
            print(f"Using default service account file: {default_path}")
            try:
                with open(default_path, 'r') as f:
                    service_account_json = json.load(f)
            except Exception as e:
                print(f"Error reading default service account file: {e}")
                return False
        else:
            print("No valid service account found in environment or default path.")
            print("Please set FIREBASE_SERVICE_ACCOUNT_KEY in your .env file")
            print("or save firebase-service-account.json in the project root.")
            return False

    try:
        # Initialize Firebase Admin with the parsed credentials
        cred = credentials.Certificate(service_account_json)
        
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        db = firestore.client()
        
        # Define all required collections
        required_collections = [
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
        
        # Force create each collection by adding a placeholder document
        for collection_name in required_collections:
            # Create collection with a placeholder document
            doc_ref = db.collection(collection_name).document("placeholder")
            doc_ref.set({
                "placeholder": True,
                "info": f"This is a placeholder for the {collection_name} collection",
                "created_by": "force_create_collections.py"
            })
            print(f"Created collection: {collection_name}")
        
        print("\nAll collections have been created successfully!")
        return True
        
    except Exception as e:
        print(f"Error creating collections: {e}")
        return False

if __name__ == "__main__":
    print("This script will force create all required collections in Firebase.")
    print("Using credentials from your .env file.")
    
    create_collections() 