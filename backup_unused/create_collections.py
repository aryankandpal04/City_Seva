#!/usr/bin/env python
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

def create_initial_collections():
    """Create initial collections in Firestore with sample documents."""
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Get the key file path from environment or use specified default
            key_file = os.environ.get('FIREBASE_KEY_FILE', 'cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json')
            
            if not os.path.exists(key_file):
                print(f"Error: Firebase key file '{key_file}' not found.")
                print("Please set FIREBASE_KEY_FILE environment variable to your key file path.")
                sys.exit(1)
                
            # Initialize Firebase
            cred = credentials.Certificate(key_file)
            firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        db = firestore.client()
        
        # Sample user document (if users collection doesn't exist yet)
        users_ref = db.collection('users')
        sample_user_id = 'sample_user_123'
        sample_user = {
            'email': 'sample@example.com',
            'first_name': 'Sample',
            'last_name': 'User',
            'username': 'sampleuser',
            'role': 'citizen',
            'is_active': True,
            'phone': '+1234567890',
            'address': '123 Sample Street, Sample City',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        
        
        # Sample category document (if categories collection doesn't exist yet)
        categories_ref = db.collection('categories')
        sample_category_id = 'sample_category_123'
        sample_category = {
            'name': 'Road Maintenance',
            'description': 'Issues related to road conditions, potholes, and street repairs',
            'department': 'Public Works',
            'icon': 'fa-road',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 1. Create complaints collection
        complaints_ref = db.collection('complaints')
        sample_complaint_id = 'sample_complaint_123'
        sample_complaint = {
            'title': 'Pothole on Main Street',
            'description': 'Large pothole near 123 Main Street creating hazard for vehicles',
            'user_id': sample_user_id,
            'category_id': sample_category_id,
            'status': 'pending',
            'priority': 'medium',
            'location': '123 Main Street',
            'latitude': 12.345678,
            'longitude': -98.765432,
            'image_path': None,
            'assigned_to_id': None,
            'assigned_at': None,
            'resolved_at': None,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        # 2. Create feedbacks collection
        feedbacks_ref = db.collection('feedbacks')
        sample_feedback_id = 'sample_feedback_123'
        sample_feedback = {
            'complaint_id': sample_complaint_id,
            'user_id': sample_user_id,
            'rating': 4,
            'comment': 'Issue was fixed promptly. Thank you!',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 3. Create notifications collection
        notifications_ref = db.collection('notifications')
        sample_notification_id = 'sample_notification_123'
        sample_notification = {
            'user_id': sample_user_id,
            'title': 'Complaint Status Updated',
            'message': 'Your complaint "Pothole on Main Street" has been updated to in_progress',
            'is_read': False,
            'complaint_id': sample_complaint_id,  # This links the notification to a complaint
            'category': 'status_update',
            'link': f'/citizen/complaints/{sample_complaint_id}',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 4. Create official_requests collection
        official_requests_ref = db.collection('official_requests')
        sample_official_request_id = 'sample_official_request_123'
        sample_official_request = {
            'user_id': sample_user_id,
            'department': 'Public Works',
            'position': 'Inspector',
            'employee_id': 'EMP12345',
            'office_phone': '+1234567890',
            'justification': 'Requesting official account to help manage road maintenance complaints',
            'status': 'pending',
            'reviewed_by': None,
            'reviewed_at': None,
            'review_notes': None,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 5. Create complaint_updates collection
        complaint_updates_ref = db.collection('complaint_updates')
        sample_update_id = 'sample_update_123'
        sample_update = {
            'complaint_id': sample_complaint_id,
            'user_id': sample_user_id,
            'status': 'in_progress',
            'comment': 'Assigned to maintenance team for repair',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 6. Create audit_logs collection
        audit_logs_ref = db.collection('audit_logs')
        sample_audit_log_id = 'sample_audit_log_123'
        sample_audit_log = {
            'user_id': sample_user_id,
            'action': 'create',
            'resource_type': 'complaint',
            'resource_id': sample_complaint_id,
            'details': 'Created new complaint: Pothole on Main Street',
            'ip_address': '192.168.1.1',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Now set the documents (this will create the collections if they don't exist)
        print("Creating sample documents in collections...")
        
        # Set users document
        users_ref.document(sample_user_id).set(sample_user)
        print("✅ Created users collection with sample user")
        
        # Set categories document
        categories_ref.document(sample_category_id).set(sample_category)
        print("✅ Created categories collection with sample category")
        
        # Set complaints document
        complaints_ref.document(sample_complaint_id).set(sample_complaint)
        print("✅ Created complaints collection with sample complaint")
        
        # Set feedbacks document
        feedbacks_ref.document(sample_feedback_id).set(sample_feedback)
        print("✅ Created feedbacks collection with sample feedback")
        
        # Set notifications document
        notifications_ref.document(sample_notification_id).set(sample_notification)
        print("✅ Created notifications collection with sample notification")
        
        # Set official_requests document
        official_requests_ref.document(sample_official_request_id).set(sample_official_request)
        print("✅ Created official_requests collection with sample request")
        
        # Set complaint_updates document
        complaint_updates_ref.document(sample_update_id).set(sample_update)
        print("✅ Created complaint_updates collection with sample update")
        
        # Set audit_logs document
        audit_logs_ref.document(sample_audit_log_id).set(sample_audit_log)
        print("✅ Created audit_logs collection with sample log")
        
        print("\nAll collections created successfully! 🎉")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_initial_collections() 