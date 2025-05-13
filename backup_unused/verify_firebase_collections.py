import os
import json
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_and_create_collections():
    """Verify that all required collections exist in Firebase and create them if they don't"""
    # Initialize Firebase Admin SDK
    try:
        # Check if Firebase Admin is already initialized
        if not firebase_admin._apps:
            # Get the path to the service account key file
            service_account_path = 'cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json'
            
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized with default app")
        else:
            print("Firebase Admin SDK already initialized")
        
        # Initialize Firestore
        db = firestore.client()
        
        # Required collections
        required_collections = [
            'users',
            'categories',
            'complaints',
            'complaint_media',
            'complaint_updates',
            'feedbacks',
            'notifications',
            'official_requests',
            'audit_logs'
        ]
        
        # Check each collection
        for collection_name in required_collections:
            print(f"Checking collection: {collection_name}...")
            
            # Get collection
            collection_ref = db.collection(collection_name)
            
            # Try to get one document to see if collection exists
            docs = list(collection_ref.limit(1).stream())
            
            if not docs:
                print(f"  - Collection {collection_name} is empty or does not exist. Creating sample document...")
                
                # Create a sample document based on collection type
                sample_doc = {}
                
                if collection_name == 'users':
                    sample_doc = {
                        'email': 'system@cityseva.example',
                        'role': 'system',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'categories':
                    sample_doc = {
                        'name': 'System',
                        'description': 'System category',
                        'department': 'System',
                        'icon': 'fa-cog'
                    }
                elif collection_name == 'complaints':
                    sample_doc = {
                        'title': 'System Test Complaint',
                        'description': 'This is a system test complaint',
                        'status': 'pending',
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'user_id': 'system',
                        'user_name': 'System User',
                        'user_email': 'system@cityseva.example',
                        'media_attachments': [
                            {
                                'media_type': 'image',
                                'file_url': 'https://via.placeholder.com/300',
                                'created_at': firestore.SERVER_TIMESTAMP
                            }
                        ],
                        'updates': [
                            {
                                'status': 'pending',
                                'comment': 'Initial complaint creation',
                                'created_at': firestore.SERVER_TIMESTAMP,
                                'user_id': 'system',
                                'user_name': 'System'
                            }
                        ]
                    }
                elif collection_name == 'complaint_media':
                    sample_doc = {
                        'complaint_id': 'system',
                        'media_type': 'image',
                        'file_url': 'https://example.com/test.jpg',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'complaint_updates':
                    sample_doc = {
                        'complaint_id': 'system',
                        'status': 'pending',
                        'comment': 'System test update',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'feedbacks':
                    sample_doc = {
                        'complaint_id': 'system',
                        'rating': 5,
                        'comment': 'System test feedback',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'notifications':
                    sample_doc = {
                        'user_id': 'system',
                        'title': 'System Test Notification',
                        'message': 'This is a system test notification',
                        'is_read': False,
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'official_requests':
                    sample_doc = {
                        'user_id': 'system',
                        'department': 'System',
                        'status': 'pending',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                elif collection_name == 'audit_logs':
                    sample_doc = {
                        'user_id': 'system',
                        'action': 'system_test',
                        'resource_type': 'system',
                        'resource_id': 'system',
                        'details': 'System test audit log',
                        'created_at': firestore.SERVER_TIMESTAMP
                    }
                
                # Add a system_ prefix to document ID to avoid conflicts
                collection_ref.document(f"system_{collection_name}_test").set(sample_doc)
                print(f"  - Created sample document in {collection_name}")
            else:
                print(f"  - Collection {collection_name} exists and contains documents")
        
        print("\nAll required collections verified and created if necessary!")
        
    except Exception as e:
        print(f"Error verifying Firebase collections: {e}")

if __name__ == "__main__":
    verify_and_create_collections() 