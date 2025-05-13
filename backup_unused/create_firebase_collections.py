"""
Create Firebase Collections using REST API
"""
import os
import sys
import json
import requests
import time
from dotenv import load_dotenv

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('cityseva.env')

def get_token():
    """Get Firebase authentication token"""
    # Get Firebase configuration from environment
    firebase_api_key = os.environ.get('FIREBASE_API_KEY')
    
    if not firebase_api_key:
        print("Error: Missing FIREBASE_API_KEY environment variable")
        return None
    
    # For web API key authentication, we create an anonymous user
    auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
    auth_payload = {"returnSecureToken": True}
    
    try:
        response = requests.post(auth_url, json=auth_payload)
        response.raise_for_status()
        id_token = response.json().get('idToken')
        if not id_token:
            print("Error: Failed to get ID token")
            return None
        return id_token
    except Exception as e:
        print(f"Error getting authentication token: {e}")
        return None

def create_firestore_collections():
    """Create all required collections in Firestore"""
    # Get Firebase configuration from environment
    firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID')
    
    if not firebase_project_id:
        print("Error: Missing FIREBASE_PROJECT_ID environment variable")
        return False
    
    # Get auth token
    token = get_token()
    if not token:
        print("Error: Failed to get authentication token")
        return False
    
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
    
    # Firestore API base URL
    base_url = f"https://firestore.googleapis.com/v1/projects/{firebase_project_id}/databases/(default)/documents"
    
    print(f"Using Firestore API URL: {base_url}")
    print(f"Project ID: {firebase_project_id}")
    
    # Create each collection with a placeholder document
    for collection in required_collections:
        collection_url = f"{base_url}/{collection}"
        
        # Create a placeholder document
        placeholder_data = {
            "fields": {
                "created_at": {
                    "timestampValue": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
                },
                "info": {
                    "stringValue": f"This is a placeholder for the {collection} collection"
                },
                "is_placeholder": {
                    "booleanValue": True
                }
            }
        }
        
        try:
            # Create the document in the collection
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                collection_url,
                headers=headers,
                json=placeholder_data
            )
            
            if response.status_code in (200, 201, 202, 409):  # 409 is conflict, means it already exists
                print(f"Successfully created collection: {collection}")
            else:
                print(f"Failed to create collection {collection}: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"Error creating collection {collection}: {e}")
    
    print("\nCollection setup complete!")
    
    # Try to export SQLite data for categories
    try:
        import sqlite3
        
        # Connect to SQLite
        db_path = os.path.join('instance', 'cityseva.db')
        if os.path.exists(db_path):
            print("\nExporting categories from SQLite...")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get categories
            cursor.execute("SELECT * FROM categories;")
            categories = cursor.fetchall()
            
            # Format for Firestore API
            for category in categories:
                cat_dict = {key: category[key] for key in category.keys()}
                
                # Convert to Firestore format
                fields = {}
                for key, value in cat_dict.items():
                    if value is None:
                        fields[key] = {"nullValue": None}
                    elif isinstance(value, int):
                        fields[key] = {"integerValue": value}
                    elif isinstance(value, float):
                        fields[key] = {"doubleValue": value}
                    elif isinstance(value, bool):
                        fields[key] = {"booleanValue": value}
                    else:
                        fields[key] = {"stringValue": str(value)}
                
                # Add to Firestore
                category_url = f"{base_url}/categories"
                doc_data = {"fields": fields}
                
                response = requests.post(
                    category_url,
                    headers=headers,
                    json=doc_data
                )
                
                if response.status_code in (200, 201, 202):
                    print(f"Added category: {cat_dict.get('name')}")
                else:
                    print(f"Failed to add category {cat_dict.get('name')}: {response.status_code}")
            
            print(f"Exported {len(categories)} categories to Firebase")
            conn.close()
        else:
            print(f"SQLite database not found at {db_path}")
    except Exception as e:
        print(f"Error exporting categories: {e}")

if __name__ == "__main__":
    create_firestore_collections() 