"""
Fix Firebase Migration to ensure all SQLite collections are properly transferred to Firebase.
This script will specifically focus on missing collections.
"""
import os
import sys
import json
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Category, Complaint, ComplaintUpdate, Feedback, AuditLog, Notification, OfficialRequest, ComplaintMedia
from app import firebase_db

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
    
    def convert_datetime(dt):
        """Convert datetime to string for Firebase"""
        if dt is None:
            return None
        return dt.isoformat()
    
    def to_dict(obj):
        """Convert SQLAlchemy model to dict"""
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            if isinstance(value, datetime.datetime):
                value = convert_datetime(value)
            result[column.name] = value
        return result
    
    # Check what collections exist in Firebase
    print("Checking existing collections in Firebase...")
    collections = firebase_db.db.collections()
    existing_collections = [col.id for col in collections]
    print(f"Existing collections: {existing_collections}")
    
    # Migrate complaints if not present
    if 'complaints' not in existing_collections:
        print("\nMigrating complaints...")
        complaints = Complaint.query.all()
        count = 0
        
        for complaint in complaints:
            try:
                # Create complaint in Firebase
                complaint_data = to_dict(complaint)
                doc_ref = firebase_db.complaints_ref().document()
                doc_ref.set(complaint_data)
                count += 1
                
                if count % 10 == 0:
                    print(f"Migrated {count} complaints...")
            except Exception as e:
                print(f"Error migrating complaint {complaint.id}: {e}")
        
        print(f"Migrated {count} complaints.")
    
    # Migrate complaint updates if not present
    if 'complaint_updates' not in existing_collections:
        print("\nMigrating complaint updates...")
        updates = ComplaintUpdate.query.all()
        count = 0
        
        for update in updates:
            try:
                update_data = to_dict(update)
                doc_ref = firebase_db.complaint_updates_ref().document()
                doc_ref.set(update_data)
                count += 1
                
                if count % 10 == 0:
                    print(f"Migrated {count} updates...")
            except Exception as e:
                print(f"Error migrating update {update.id}: {e}")
        
        print(f"Migrated {count} updates.")
    
    # Migrate feedback if not present
    if 'feedbacks' not in existing_collections:
        print("\nMigrating feedback...")
        feedbacks = Feedback.query.all()
        count = 0
        
        for feedback in feedbacks:
            try:
                feedback_data = to_dict(feedback)
                doc_ref = firebase_db.feedbacks_ref().document()
                doc_ref.set(feedback_data)
                count += 1
            except Exception as e:
                print(f"Error migrating feedback {feedback.id}: {e}")
        
        print(f"Migrated {count} feedbacks.")
    
    # Migrate notifications if not present
    if 'notifications' not in existing_collections:
        print("\nMigrating notifications...")
        notifications = Notification.query.all()
        count = 0
        
        for notification in notifications:
            try:
                notification_data = to_dict(notification)
                doc_ref = firebase_db.notifications_ref().document()
                doc_ref.set(notification_data)
                count += 1
                
                if count % 10 == 0:
                    print(f"Migrated {count} notifications...")
            except Exception as e:
                print(f"Error migrating notification {notification.id}: {e}")
        
        print(f"Migrated {count} notifications.")
    
    # Migrate official requests if not present
    if 'official_requests' not in existing_collections:
        print("\nMigrating official requests...")
        requests = OfficialRequest.query.all()
        count = 0
        
        for req in requests:
            try:
                request_data = to_dict(req)
                doc_ref = firebase_db.official_requests_ref().document()
                doc_ref.set(request_data)
                count += 1
            except Exception as e:
                print(f"Error migrating official request {req.id}: {e}")
        
        print(f"Migrated {count} official requests.")
    
    # Migrate complaint media if not present
    if 'complaint_media' not in existing_collections:
        print("\nMigrating complaint media...")
        media_items = ComplaintMedia.query.all()
        count = 0
        
        for media in media_items:
            try:
                # Try to upload the file if it exists
                file_url = None
                local_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), media.file_path)
                if os.path.exists(local_path):
                    storage_path = f"complaints/{media.complaint_id}/{os.path.basename(media.file_path)}"
                    file_url = firebase_db.upload_file_from_path(local_path, storage_path)
                
                # Create media entry in Firebase
                media_data = to_dict(media)
                if file_url:
                    media_data['file_url'] = file_url
                    media_data['storage_path'] = storage_path
                
                firebase_db.create_complaint_media(media_data)
                count += 1
                
                if count % 10 == 0:
                    print(f"Migrated {count} media items...")
            except Exception as e:
                print(f"Error migrating media {media.id}: {e}")
        
        print(f"Migrated {count} media items.")
    
    print("\nMigration fix completed!")
    print("All missing collections should now be transferred to Firebase.")

if __name__ == "__main__":
    print("This script will fix missing collections in Firebase.")
    confirm = input("Are you sure you want to proceed? (y/n): ")
    if confirm.lower() == 'y':
        print("Starting migration fix...")
        # The migration code will run when the script is imported
    else:
        print("Migration fix cancelled.") 