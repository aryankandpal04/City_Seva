"""
Migrate all data from SQLite to Firebase Firestore.
Run this script once to transfer all existing data to Firebase.
After running this script, the application will use Firebase exclusively.
"""
import os
import sys
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Category, Complaint, ComplaintUpdate, Feedback, AuditLog, Notification, OfficialRequest, ComplaintMedia
from app import firebase_db
from flask import current_app
import json

# Initialize app with 'development' config
app = create_app('development')
with app.app_context():
    # Initialize Firebase (only if not already initialized)
    if not firebase_admin._apps:
        print("Initializing Firebase directly...")
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    
    # Make sure firebase_db is initialized
    if not hasattr(firebase_db, 'db') or firebase_db.db is None:
        print("Initializing firebase_db...")
        firebase_db.db = firestore.client()
    
    # Helper functions
    def convert_datetime(dt):
        """Convert datetime to string for Firebase"""
        if dt is None:
            return None
        return dt.isoformat()
    
    def migrate_users():
        """Migrate users from SQLite to Firebase"""
        print("Migrating users...")
        users = User.query.all()
        count = 0
        skip_count = 0
        
        for user in users:
            try:
                # Check if user already exists in Firebase (by email)
                existing_user = firebase_db.get_user_by_email(user.email)
                if existing_user:
                    print(f"User {user.email} already exists in Firebase. Skipping.")
                    skip_count += 1
                    continue
                
                # Create user in Firebase
                user_data = {
                    'email': user.email,
                    'username': user.username,
                    # We can't migrate passwords directly due to different hashing methods
                    # Users will need to reset their passwords
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone,
                    'address': user.address,
                    'role': user.role,
                    'department': user.department,
                    'is_active': user.is_active,
                    'is_online': user.is_online,
                    'created_at': convert_datetime(user.created_at),
                    'last_login': convert_datetime(user.last_login),
                    # Store the original SQLite ID for reference during migration
                    'sqlite_id': user.id
                }
                
                # Create user in Firebase
                doc_ref = firebase_db.users_ref().document()
                doc_ref.set(user_data)
                count += 1
                
                # Print progress
                if count % 10 == 0:
                    print(f"Migrated {count} users...")
            except Exception as e:
                print(f"Error migrating user {user.id}: {e}")
        
        print(f"Migrated {count} users. Skipped {skip_count} users.")
        return count
    
    def migrate_categories():
        """Migrate categories from SQLite to Firebase"""
        print("Migrating categories...")
        categories = Category.query.all()
        count = 0
        category_map = {}  # Maps SQLite ID to Firebase ID
        
        for category in categories:
            try:
                # Check if category already exists by name
                query = firebase_db.categories_ref().where('name', '==', category.name).limit(1)
                docs = query.get()
                
                if len(docs) > 0:
                    # Category exists, use its ID
                    firebase_id = docs[0].id
                    category_map[category.id] = firebase_id
                    print(f"Category {category.name} already exists in Firebase. Using existing ID.")
                    continue
                
                # Create category in Firebase
                category_data = {
                    'name': category.name,
                    'description': category.description,
                    'department': category.department,
                    'icon': category.icon,
                    'sqlite_id': category.id
                }
                
                # Create category in Firebase
                doc_ref = firebase_db.categories_ref().document()
                doc_ref.set(category_data)
                category_map[category.id] = doc_ref.id
                count += 1
            except Exception as e:
                print(f"Error migrating category {category.id}: {e}")
        
        print(f"Migrated {count} categories.")
        return category_map
    
    def migrate_complaints(user_map, category_map):
        """Migrate complaints from SQLite to Firebase"""
        print("Migrating complaints...")
        complaints = Complaint.query.all()
        count = 0
        complaint_map = {}  # Maps SQLite ID to Firebase ID
        
        for complaint in complaints:
            try:
                # Map SQLite IDs to Firebase IDs
                user_id = user_map.get(complaint.user_id)
                if not user_id:
                    print(f"User {complaint.user_id} not found in user_map. Skipping complaint {complaint.id}.")
                    continue
                
                category_id = category_map.get(complaint.category_id)
                if not category_id:
                    print(f"Category {complaint.category_id} not found in category_map. Skipping complaint {complaint.id}.")
                    continue
                
                assigned_to_id = None
                if complaint.assigned_to_id:
                    assigned_to_id = user_map.get(complaint.assigned_to_id)
                
                # Create complaint in Firebase
                complaint_data = {
                    'title': complaint.title,
                    'description': complaint.description,
                    'location': complaint.location,
                    'latitude': complaint.latitude,
                    'longitude': complaint.longitude,
                    'category_id': category_id,
                    'status': complaint.status,
                    'priority': complaint.priority,
                    'user_id': user_id,
                    'assigned_to_id': assigned_to_id,
                    'assigned_at': convert_datetime(complaint.assigned_at),
                    'created_at': convert_datetime(complaint.created_at),
                    'updated_at': convert_datetime(complaint.updated_at),
                    'resolved_at': convert_datetime(complaint.resolved_at),
                    'sqlite_id': complaint.id
                }
                
                # Create complaint in Firebase
                doc_ref = firebase_db.complaints_ref().document()
                doc_ref.set(complaint_data)
                complaint_map[complaint.id] = doc_ref.id
                count += 1
                
                # Print progress
                if count % 10 == 0:
                    print(f"Migrated {count} complaints...")
            except Exception as e:
                print(f"Error migrating complaint {complaint.id}: {e}")
        
        print(f"Migrated {count} complaints.")
        return complaint_map
    
    def migrate_complaint_media(complaint_map):
        """Migrate complaint media from SQLite to Firebase"""
        print("Migrating complaint media...")
        media_items = ComplaintMedia.query.all()
        count = 0
        
        for media in media_items:
            try:
                # Map SQLite IDs to Firebase IDs
                complaint_id = complaint_map.get(media.complaint_id)
                if not complaint_id:
                    print(f"Complaint {media.complaint_id} not found in complaint_map. Skipping media {media.id}.")
                    continue
                
                # Upload the file to Firebase Storage
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], media.file_path)
                
                if not os.path.exists(local_path):
                    print(f"Media file {local_path} does not exist. Skipping.")
                    continue
                
                # Generate storage path
                filename = os.path.basename(media.file_path)
                storage_path = f"complaints/{complaint_id}/{filename}"
                
                # Upload to Firebase Storage
                file_url = firebase_db.upload_file_from_path(local_path, storage_path)
                
                if not file_url:
                    print(f"Failed to upload {local_path} to Firebase Storage. Skipping.")
                    continue
                
                # Create media entry in Firebase
                media_data = {
                    'complaint_id': complaint_id,
                    'file_url': file_url,
                    'storage_path': storage_path,
                    'media_type': media.media_type,
                    'created_at': convert_datetime(media.created_at),
                    'sqlite_id': media.id
                }
                
                # Save to Firestore
                firebase_db.create_complaint_media(media_data)
                count += 1
                
                # Print progress
                if count % 10 == 0:
                    print(f"Migrated {count} media items...")
            except Exception as e:
                print(f"Error migrating media {media.id}: {e}")
        
        print(f"Migrated {count} media items.")
        return count
    
    def migrate_complaint_updates(complaint_map, user_map):
        """Migrate complaint updates from SQLite to Firebase"""
        print("Migrating complaint updates...")
        updates = ComplaintUpdate.query.all()
        count = 0
        
        for update in updates:
            try:
                # Map SQLite IDs to Firebase IDs
                complaint_id = complaint_map.get(update.complaint_id)
                if not complaint_id:
                    print(f"Complaint {update.complaint_id} not found in complaint_map. Skipping update {update.id}.")
                    continue
                
                user_id = user_map.get(update.user_id)
                if not user_id:
                    print(f"User {update.user_id} not found in user_map. Skipping update {update.id}.")
                    continue
                
                # Create update in Firebase
                update_data = {
                    'complaint_id': complaint_id,
                    'user_id': user_id,
                    'status': update.status,
                    'comment': update.comment,
                    'created_at': convert_datetime(update.created_at),
                    'sqlite_id': update.id
                }
                
                # Save to Firestore
                doc_ref = firebase_db.complaint_updates_ref().document()
                doc_ref.set(update_data)
                count += 1
                
                # Print progress
                if count % 10 == 0:
                    print(f"Migrated {count} updates...")
            except Exception as e:
                print(f"Error migrating update {update.id}: {e}")
        
        print(f"Migrated {count} updates.")
        return count
    
    def migrate_feedback(complaint_map, user_map):
        """Migrate feedback from SQLite to Firebase"""
        print("Migrating feedback...")
        feedbacks = Feedback.query.all()
        count = 0
        
        for feedback in feedbacks:
            try:
                # Map SQLite IDs to Firebase IDs
                complaint_id = complaint_map.get(feedback.complaint_id)
                if not complaint_id:
                    print(f"Complaint {feedback.complaint_id} not found in complaint_map. Skipping feedback {feedback.id}.")
                    continue
                
                user_id = user_map.get(feedback.user_id)
                if not user_id:
                    print(f"User {feedback.user_id} not found in user_map. Skipping feedback {feedback.id}.")
                    continue
                
                # Create feedback in Firebase
                feedback_data = {
                    'complaint_id': complaint_id,
                    'user_id': user_id,
                    'rating': feedback.rating,
                    'comment': feedback.comment,
                    'created_at': convert_datetime(feedback.created_at),
                    'sqlite_id': feedback.id
                }
                
                # Save to Firestore
                doc_ref = firebase_db.feedbacks_ref().document()
                doc_ref.set(feedback_data)
                count += 1
            except Exception as e:
                print(f"Error migrating feedback {feedback.id}: {e}")
        
        print(f"Migrated {count} feedbacks.")
        return count
    
    def migrate_audit_logs(user_map):
        """Migrate audit logs from SQLite to Firebase"""
        print("Migrating audit logs...")
        logs = AuditLog.query.all()
        count = 0
        
        for log in logs:
            try:
                # Map SQLite user ID to Firebase ID
                user_id = None
                if log.user_id:
                    user_id = user_map.get(log.user_id)
                
                # Create audit log in Firebase
                log_data = {
                    'user_id': user_id,
                    'action': log.action,
                    'resource_type': log.resource_type,
                    'resource_id': str(log.resource_id) if log.resource_id else None,
                    'details': log.details,
                    'ip_address': log.ip_address,
                    'created_at': convert_datetime(log.created_at),
                    'sqlite_id': log.id
                }
                
                # Save to Firestore
                firebase_db.create_audit_log(log_data)
                count += 1
                
                # Print progress
                if count % 100 == 0:
                    print(f"Migrated {count} audit logs...")
            except Exception as e:
                print(f"Error migrating audit log {log.id}: {e}")
        
        print(f"Migrated {count} audit logs.")
        return count
    
    def migrate_notifications(user_map):
        """Migrate notifications from SQLite to Firebase"""
        print("Migrating notifications...")
        notifications = Notification.query.all()
        count = 0
        
        for notification in notifications:
            try:
                # Map SQLite user ID to Firebase ID
                user_id = user_map.get(notification.user_id)
                if not user_id:
                    print(f"User {notification.user_id} not found in user_map. Skipping notification {notification.id}.")
                    continue
                
                # Create notification in Firebase
                notification_data = {
                    'user_id': user_id,
                    'title': notification.title,
                    'message': notification.message,
                    'is_read': notification.is_read,
                    'created_at': convert_datetime(notification.created_at),
                    'sqlite_id': notification.id
                }
                
                # Save to Firestore
                doc_ref = firebase_db.notifications_ref().document()
                doc_ref.set(notification_data)
                count += 1
                
                # Print progress
                if count % 100 == 0:
                    print(f"Migrated {count} notifications...")
            except Exception as e:
                print(f"Error migrating notification {notification.id}: {e}")
        
        print(f"Migrated {count} notifications.")
        return count
    
    def migrate_official_requests(user_map):
        """Migrate official requests from SQLite to Firebase"""
        print("Migrating official requests...")
        requests = OfficialRequest.query.all()
        count = 0
        
        for request in requests:
            try:
                # Map SQLite user IDs to Firebase IDs
                user_id = user_map.get(request.user_id)
                if not user_id:
                    print(f"User {request.user_id} not found in user_map. Skipping request {request.id}.")
                    continue
                
                reviewed_by = None
                if request.reviewed_by:
                    reviewed_by = user_map.get(request.reviewed_by)
                
                # Create official request in Firebase
                request_data = {
                    'user_id': user_id,
                    'department': request.department,
                    'position': request.position,
                    'employee_id': request.employee_id,
                    'office_phone': request.office_phone,
                    'justification': request.justification,
                    'status': request.status,
                    'reviewed_by': reviewed_by,
                    'reviewed_at': convert_datetime(request.reviewed_at),
                    'review_notes': request.review_notes,
                    'created_at': convert_datetime(request.created_at),
                    'sqlite_id': request.id
                }
                
                # Save to Firestore
                doc_ref = firebase_db.official_requests_ref().document()
                doc_ref.set(request_data)
                count += 1
            except Exception as e:
                print(f"Error migrating official request {request.id}: {e}")
        
        print(f"Migrated {count} official requests.")
        return count
    
    def create_id_mapping_file(user_map, category_map, complaint_map):
        """Create a JSON file with ID mappings for reference"""
        print("Creating ID mapping file...")
        
        mapping = {
            'users': user_map,
            'categories': category_map,
            'complaints': complaint_map
        }
        
        with open('firebase_id_mapping.json', 'w') as f:
            json.dump(mapping, f, indent=2)
        
        print("ID mapping file created: firebase_id_mapping.json")
    
    # Run the migration
    print("Starting migration from SQLite to Firebase...")
    
    # Build ID mappings
    user_map = {}  # SQLite ID -> Firebase ID
    
    # Migrate users first to get user mappings
    print("\n1. Migrating users")
    users = User.query.all()
    for user in users:
        # Check if user already exists in Firebase (by email)
        existing_user = firebase_db.get_user_by_email(user.email)
        if existing_user:
            user_map[user.id] = existing_user['id']
            print(f"User {user.email} already exists in Firebase. ID: {existing_user['id']}")
        else:
            # Create user data
            user_data = {
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'address': user.address,
                'role': user.role,
                'department': user.department,
                'is_active': user.is_active,
                'is_online': user.is_online,
                'created_at': convert_datetime(user.created_at),
                'last_login': convert_datetime(user.last_login),
                'sqlite_id': user.id
            }
            
            # Create user in Firebase
            doc_ref = firebase_db.users_ref().document()
            doc_ref.set(user_data)
            user_map[user.id] = doc_ref.id
            print(f"Created user in Firebase: {user.email} - ID: {doc_ref.id}")
    
    print(f"\nMigrated {len(user_map)} users.")
    
    # Migrate categories
    print("\n2. Migrating categories")
    category_map = migrate_categories()
    
    # Migrate complaints
    print("\n3. Migrating complaints")
    complaint_map = migrate_complaints(user_map, category_map)
    
    # Migrate complaint media
    print("\n4. Migrating complaint media")
    migrate_complaint_media(complaint_map)
    
    # Migrate complaint updates
    print("\n5. Migrating complaint updates")
    migrate_complaint_updates(complaint_map, user_map)
    
    # Migrate feedback
    print("\n6. Migrating feedback")
    migrate_feedback(complaint_map, user_map)
    
    # Migrate audit logs
    print("\n7. Migrating audit logs")
    migrate_audit_logs(user_map)
    
    # Migrate notifications
    print("\n8. Migrating notifications")
    migrate_notifications(user_map)
    
    # Migrate official requests
    print("\n9. Migrating official requests")
    migrate_official_requests(user_map)
    
    # Create ID mapping file for reference
    create_id_mapping_file(user_map, category_map, complaint_map)
    
    print("\nMigration complete!")
    print("All data has been migrated from SQLite to Firebase.")
    print("You can now configure the application to use Firebase exclusively.")

if __name__ == "__main__":
    print("This script will migrate all data from SQLite to Firebase.")
    print("Make sure your Firebase configuration is correct in the .env or config file.")
    print("This process may take some time depending on the amount of data.")
    print()
    
    confirm = input("Are you sure you want to proceed? (y/n): ")
    if confirm.lower() == 'y':
        print("Starting migration...")
        # The migration code will run when the script is imported
    else:
        print("Migration cancelled.") 