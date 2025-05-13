import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import current_app
from datetime import datetime

# Firebase instance
firebase_app = None
db = None
bucket = None

def init_app(app):
    """Initialize Firebase with Flask app"""
    global firebase_app, db, bucket
    
    # Check if Firebase is already initialized
    if firebase_app:
        return
    
    try:
        # Get the path to the service account key file
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        
        # If it's a JSON string, write it to a temp file
        if service_account_path.startswith('{'):
            service_account_data = json.loads(service_account_path)
            service_account_path = 'temp_service_account.json'
            with open(service_account_path, 'w') as f:
                json.dump(service_account_data, f)
        
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': app.config.get('FIREBASE_STORAGE_BUCKET')
        })
        
        # Initialize Firestore and Storage
        db = firestore.client()
        bucket = storage.bucket()
        
        app.logger.info('Firebase initialized successfully')
    except Exception as e:
        app.logger.error(f'Error initializing Firebase: {e}')
        raise

# Helper functions for document manipulation

def to_dict(doc_snapshot):
    """Convert document snapshot to dict with id"""
    data = doc_snapshot.to_dict()
    data['id'] = doc_snapshot.id
    return data

def to_timestamp(dt):
    """Convert datetime to Firestore timestamp"""
    if isinstance(dt, datetime):
        return firestore.SERVER_TIMESTAMP if dt is None else dt
    return dt

def from_timestamp(timestamp):
    """Convert Firestore timestamp to datetime"""
    if hasattr(timestamp, 'todate'):
        return timestamp.todate()
    return timestamp

# Collection references
def users_ref():
    return db.collection('users')

def categories_ref():
    return db.collection('categories')

def complaints_ref():
    return db.collection('complaints')

def complaint_updates_ref():
    return db.collection('complaint_updates')

def feedbacks_ref():
    return db.collection('feedbacks')

def audit_logs_ref():
    return db.collection('audit_logs')

def notifications_ref():
    return db.collection('notifications')

def official_requests_ref():
    return db.collection('official_requests')

# File upload to Firebase Storage
def upload_file(file, path):
    """Upload file to Firebase Storage and return public URL"""
    if not file:
        return None
    
    blob = bucket.blob(path)
    blob.upload_from_file(file)
    blob.make_public()
    return blob.public_url

def upload_file_from_path(file_path, storage_path):
    """Upload a file from disk to Firebase Storage and return public URL"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    blob = bucket.blob(storage_path)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url

# Collection references for complaint media
def complaint_media_ref():
    """Get reference to complaint_media collection"""
    return db.collection('complaint_media')

# Complaint media methods
def get_complaint_media(complaint_id):
    """Get all media for a complaint"""
    query = complaint_media_ref().where('complaint_id', '==', complaint_id).order_by('created_at')
    docs = query.get()
    return [to_dict(doc) for doc in docs]

def create_complaint_media(media_data):
    """Create a new complaint media entry"""
    media_data['created_at'] = firestore.SERVER_TIMESTAMP
    doc_ref = complaint_media_ref().document()
    doc_ref.set(media_data)
    media_data['id'] = doc_ref.id
    return media_data

def delete_complaint_media(media_id):
    """Delete a complaint media entry"""
    media_ref = complaint_media_ref().document(media_id)
    media_doc = media_ref.get()
    
    if media_doc.exists:
        media_data = to_dict(media_doc)
        
        # Delete the file from Storage if file_path exists
        if 'storage_path' in media_data:
            try:
                blob = bucket.blob(media_data['storage_path'])
                blob.delete()
            except Exception as e:
                current_app.logger.error(f"Error deleting file from Storage: {e}")
        
        # Delete the document
        media_ref.delete()
        return True
    
    return False

def delete_complaint_media_for_complaint(complaint_id):
    """Delete all media entries for a complaint"""
    try:
        media_refs = complaint_media_ref().where('complaint_id', '==', complaint_id).stream()
        
        for media_doc in media_refs:
            media_id = media_doc.id
            delete_complaint_media(media_id)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting media for complaint {complaint_id}: {e}")
        return False

# User methods
def get_user(user_id):
    """Get user by ID"""
    doc = users_ref().document(user_id).get()
    return to_dict(doc) if doc.exists else None

def get_user_by_email(email):
    """Get user by email"""
    query = users_ref().where('email', '==', email).limit(1)
    docs = query.get()
    return to_dict(docs[0]) if docs else None

def create_user(user_data):
    """Create a new user"""
    user_data['created_at'] = firestore.SERVER_TIMESTAMP
    doc_ref = users_ref().document()
    doc_ref.set(user_data)
    user_data['id'] = doc_ref.id
    return user_data

def update_user(user_id, user_data):
    """Update user data"""
    user_data['updated_at'] = firestore.SERVER_TIMESTAMP
    users_ref().document(user_id).update(user_data)
    return get_user(user_id)

# Category methods
def get_all_categories():
    """Get all categories"""
    docs = categories_ref().get()
    return [to_dict(doc) for doc in docs]

def get_category(category_id):
    """Get category by ID"""
    doc = categories_ref().document(category_id).get()
    return to_dict(doc) if doc.exists else None

def create_category(category_data):
    """Create a new category"""
    doc_ref = categories_ref().document()
    doc_ref.set(category_data)
    category_data['id'] = doc_ref.id
    return category_data

# Complaint methods
def get_all_complaints(limit=None, offset=None):
    """Get all complaints with optional pagination"""
    query = complaints_ref().order_by('created_at', direction=firestore.Query.DESCENDING)
    
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    
    docs = query.get()
    return [to_dict(doc) for doc in docs]

def get_complaint(complaint_id):
    """Get complaint by ID"""
    doc = complaints_ref().document(complaint_id).get()
    return to_dict(doc) if doc.exists else None

def create_complaint(complaint_data):
    """Create a new complaint"""
    complaint_data['created_at'] = firestore.SERVER_TIMESTAMP
    complaint_data['updated_at'] = firestore.SERVER_TIMESTAMP
    doc_ref = complaints_ref().document()
    doc_ref.set(complaint_data)
    complaint_data['id'] = doc_ref.id
    return complaint_data

def update_complaint(complaint_id, complaint_data):
    """Update complaint data"""
    complaint_data['updated_at'] = firestore.SERVER_TIMESTAMP
    complaints_ref().document(complaint_id).update(complaint_data)
    return get_complaint(complaint_id)

def get_user_complaints(user_id, limit=None):
    """Get complaints for a specific user"""
    query = complaints_ref().where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
    
    if limit:
        query = query.limit(limit)
    
    docs = query.get()
    return [to_dict(doc) for doc in docs]

def create_audit_log(audit_data):
    """Create an audit log entry in Firestore"""
    audit_data['created_at'] = firestore.SERVER_TIMESTAMP
    doc_ref = audit_logs_ref().document()
    doc_ref.set(audit_data)
    return True 