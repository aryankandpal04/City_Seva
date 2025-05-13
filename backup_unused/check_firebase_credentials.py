"""
Firebase Credentials Checker

This script checks if the Firebase credentials are valid.
"""
import json
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

def check_key_file(key_path):
    """Check if the key file exists and has valid JSON format"""
    print(f"Checking key file: {key_path}")
    
    # Check if file exists
    if not os.path.exists(key_path):
        print(f"Error: Key file not found at {key_path}")
        return False
    
    # Check if file is valid JSON
    try:
        with open(key_path, 'r') as f:
            key_data = json.load(f)
        
        # Check required fields
        required_fields = [
            "type", "project_id", "private_key_id", "private_key", 
            "client_email", "client_id", "auth_uri", "token_uri", 
            "auth_provider_x509_cert_url", "client_x509_cert_url"
        ]
        
        for field in required_fields:
            if field not in key_data:
                print(f"Error: Key file missing required field: {field}")
                return False
        
        # Check if private_key is valid
        if not key_data["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
            print("Error: Invalid private key format")
            return False
        
        print("Key file structure looks valid.")
        print(f"Project ID: {key_data['project_id']}")
        print(f"Client Email: {key_data['client_email']}")
        return True
    
    except json.JSONDecodeError:
        print("Error: Key file is not valid JSON")
        return False
    except Exception as e:
        print(f"Error checking key file: {e}")
        return False

def check_firebase_connection(key_path):
    """Try to connect to Firebase using the key file"""
    print("\nTrying to connect to Firebase...")
    
    try:
        # Initialize Firebase
        cred = credentials.Certificate(key_path)
        try:
            app = firebase_admin.initialize_app(cred)
        except ValueError:
            # App already initialized, get the default app
            app = firebase_admin.get_app()
        
        # Try to access Firestore
        db = firestore.client()
        collections = db.collections()
        collection_names = [collection.id for collection in collections]
        
        print("Successfully connected to Firebase!")
        print(f"Available collections: {', '.join(collection_names) if collection_names else 'No collections found'}")
        
        # Cleanup
        firebase_admin.delete_app(app)
        return True
    
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        return False

def main():
    """Main function"""
    key_path = "cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json"
    
    # Check if key file path is provided as argument
    if len(sys.argv) > 1:
        key_path = sys.argv[1]
    
    # Check key file
    if not check_key_file(key_path):
        return
    
    # Check Firebase connection
    check_firebase_connection(key_path)

if __name__ == "__main__":
    main() 