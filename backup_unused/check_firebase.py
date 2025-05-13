"""
Check what collections exist in Firebase Firestore
"""
import os
import sys
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, firebase_db

# Initialize app
app = create_app('development')

with app.app_context():
    # Initialize Firebase if not already initialized
    if not firebase_admin._apps:
        print("Initializing Firebase directly...")
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        if service_account_path.startswith('{'):
            service_account_data = json.loads(service_account_path)
            service_account_path = 'temp_service_account.json'
            with open(service_account_path, 'w') as f:
                json.dump(service_account_data, f)
        
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': app.config.get('FIREBASE_STORAGE_BUCKET')
        })
    
    # Make sure firebase_db is initialized
    if not hasattr(firebase_db, 'db') or firebase_db.db is None:
        firebase_db.db = firestore.client()
    
    # Get and print collections
    print("\nCollections in Firebase:")
    collections = firebase_db.db.collections()
    existing_collections = [col.id for col in collections]
    print(existing_collections)
    
    # Check document counts in each collection
    print("\nDocument counts per collection:")
    for col_name in existing_collections:
        docs = firebase_db.db.collection(col_name).get()
        doc_count = len(docs)
        print(f"- {col_name}: {doc_count} documents")
        
        # Show a sample document from each collection (if available)
        if doc_count > 0:
            print(f"  Sample document from {col_name}:")
            sample_doc = docs[0].to_dict()
            for key, value in sample_doc.items():
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 50:
                    str_value = str_value[:50] + "..."
                print(f"    {key}: {str_value}")
    
    print("\nFirebase inspection complete!") 