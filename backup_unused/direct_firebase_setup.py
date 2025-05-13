"""
Direct Firebase Setup - Creates all required collections directly in Firebase
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('cityseva.env')

def setup_firebase_collections():
    """Create all required collections in Firebase Realtime Database"""
    
    # Get Firebase configuration from environment
    firebase_api_key = os.environ.get('FIREBASE_API_KEY')
    firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID')
    database_url = os.environ.get('FIREBASE_DATABASE_URL')
    
    if not all([firebase_api_key, firebase_project_id, database_url]):
        print("Error: Missing required Firebase configuration")
        print("Please make sure the following environment variables are set:")
        print("- FIREBASE_API_KEY")
        print("- FIREBASE_PROJECT_ID")
        print("- FIREBASE_DATABASE_URL")
        return False
    
    # If database URL doesn't end with /, add it
    if not database_url.endswith('/'):
        database_url += '/'
    
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
    
    print(f"Using Firebase Database URL: {database_url}")
    print(f"Project ID: {firebase_project_id}")
    
    # Create each collection with a placeholder document
    for collection in required_collections:
        collection_url = f"{database_url}{collection}.json"
        
        # Create a placeholder document
        placeholder_data = {
            "placeholder": {
                "created_at": {"seconds": int(time.time()), "nanoseconds": 0},
                "info": f"This is a placeholder for the {collection} collection",
                "is_placeholder": True
            }
        }
        
        try:
            # Check if collection already exists
            response = requests.get(collection_url)
            if response.status_code == 200 and response.json():
                print(f"Collection '{collection}' already exists")
                continue
            
            # Create the collection with the placeholder
            response = requests.put(
                collection_url, 
                data=json.dumps(placeholder_data),
                params={"auth": firebase_api_key}
            )
            
            if response.status_code in (200, 201):
                print(f"Successfully created collection: {collection}")
            else:
                print(f"Failed to create collection {collection}: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"Error creating collection {collection}: {e}")
    
    print("\nCollection setup complete!")

if __name__ == "__main__":
    import time
    setup_firebase_collections() 