"""
Manually create Firebase collections

This script manually creates all required collections in Firebase.
Use this when other migration methods fail.
"""
import os
import sys
import json
import requests
from getpass import getpass

# Collections to create
REQUIRED_COLLECTIONS = [
    'complaints', 
    'notifications', 
    'official_requests', 
    'complaint_updates', 
    'feedbacks', 
    'complaint_media',
    'categories',
    'users',
    'audit_logs'
]

def get_firebase_config():
    """Get Firebase configuration"""
    # Ask for Firebase project details
    print("Enter your Firebase project details:")
    project_id = input("Project ID: ")
    api_key = input("Web API Key: ")
    email = input("Firebase Admin Email: ")
    password = getpass("Firebase Admin Password: ")
    
    return {
        "project_id": project_id,
        "api_key": api_key,
        "email": email,
        "password": password
    }

def get_auth_token(api_key, email, password):
    """Get Firebase authentication token"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get("idToken")
    except Exception as e:
        print(f"Error getting authentication token: {e}")
        return None

def create_collection(project_id, token, collection_name):
    """Create a collection by adding a dummy document"""
    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection_name}"
    
    # Create a dummy document that we'll delete after
    dummy_doc_id = "dummy_initialization_doc"
    doc_url = f"{url}/{dummy_doc_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Add a timestamp field
    data = {
        "fields": {
            "created_at": {
                "stringValue": f"{datetime.now().isoformat()}"
            },
            "description": {
                "stringValue": "This document was created to initialize the collection and will be deleted."
            }
        }
    }
    
    try:
        # Create the document
        response = requests.post(doc_url, json=data, headers=headers)
        response.raise_for_status()
        print(f"Created collection: {collection_name}")
        
        # Delete the document 
        response = requests.delete(doc_url, headers=headers)
        response.raise_for_status()
        print(f"Removed initialization document from {collection_name}")
        
        return True
    except Exception as e:
        print(f"Error creating collection {collection_name}: {e}")
        return False

def main():
    """Main function"""
    print("This script will manually create all required collections in Firebase.")
    print("You need to have Firebase admin credentials to proceed.")
    print()
    
    # Get Firebase configuration
    config = get_firebase_config()
    
    # Get authentication token
    print("
Getting authentication token...")
    token = get_auth_token(config["api_key"], config["email"], config["password"])
    
    if not token:
        print("Failed to get authentication token. Exiting.")
        return
    
    # Create collections
    print("
Creating collections...")
    success_count = 0
    
    for collection in REQUIRED_COLLECTIONS:
        print(f"
Creating collection: {collection}")
        if create_collection(config["project_id"], token, collection):
            success_count += 1
    
    print(f"
Collection creation complete! Successfully created {success_count}/{len(REQUIRED_COLLECTIONS)} collections.")

if __name__ == "__main__":
    from datetime import datetime
    main()
