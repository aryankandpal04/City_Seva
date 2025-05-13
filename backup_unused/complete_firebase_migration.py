"""
Complete Firebase Migration - Transfers all data from SQLite to Firebase
This script ensures all collections are created in Firebase with proper data
"""
import os
import sys
import json
import sqlite3
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Category, Complaint, ComplaintUpdate, Feedback, AuditLog, Notification, OfficialRequest, ComplaintMedia
from app import firebase_db

# Initialize app
app = create_app('development')

def init_firebase():
    """Initialize Firebase with proper configuration"""
    if not firebase_admin._apps:
        print("Initializing Firebase...")
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        
        # If it's a JSON string, write it to a temp file
        if isinstance(service_account_path, str) and service_account_path.startswith('{'):
            service_account_data = json.loads(service_account_path)
            service_account_path = 'temp_service_account.json'
            with open(service_account_path, 'w') as f:
                json.dump(service_account_data, f)
        
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': app.config.get('FIREBASE_STORAGE_BUCKET')
        })
    
    # Initialize firebase_db
    if not hasattr(firebase_db, 'db') or firebase_db.db is None:
        firebase_db.db = firestore.client()
    
    if not hasattr(firebase_db, 'bucket') or firebase_db.bucket is None:
        firebase_db.bucket = storage.bucket()
    
    return firebase_db.db

def convert_datetime(dt):
    """Convert datetime to string for Firebase"""
    if dt is None:
        return None
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return dt

def get_existing_collections():
    """Get list of existing collections in Firebase"""
    collections = firebase_db.db.collections()
    return [col.id for col in collections]

def get_sqlite_tables():
    """Get list of tables from SQLite database"""
    db_path = os.path.join('instance', 'cityseva.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()
    return tables

def query_sqlite_table(table_name):
    """Get all rows from a SQLite table"""
    db_path = os.path.join('instance', 'cityseva.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    
    # Convert to list of dicts
    result = []
    for row in rows:
        row_dict = {key: row[key] for key in row.keys()}
        # Convert datetime strings to isoformat
        for key, value in row_dict.items():
            if isinstance(value, str) and (
                'date' in key.lower() or 
                'time' in key.lower() or 
                key in ['created_at', 'updated_at', 'resolved_at', 'assigned_at', 'last_login', 'reviewed_at']
            ):
                try:
                    dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
                    row_dict[key] = dt.isoformat()
                except (ValueError, TypeError):
                    pass
        result.append(row_dict)
    
    conn.close()
    return result

def migrate_table_to_firebase(table_name, collection_name=None):
    """Migrate a SQLite table to a Firebase collection"""
    if collection_name is None:
        collection_name = table_name
    
    print(f"Migrating {table_name} to {collection_name}...")
    
    # Get data from SQLite
    rows = query_sqlite_table(table_name)
    if not rows:
        print(f"No data found in {table_name}. Skipping.")
        return 0
    
    # Create collection reference
    collection_ref = firebase_db.db.collection(collection_name)
    
    # Add documents to collection
    count = 0
    for row in rows:
        # Convert all datetime values to strings
        for key, value in row.items():
            if isinstance(value, datetime.datetime):
                row[key] = convert_datetime(value)
        
        # Add original SQLite ID for reference
        row['sqlite_id'] = row.get('id')
        
        # Add to Firebase
        doc_ref = collection_ref.document()
        doc_ref.set(row)
        count += 1
        
        # Print progress
        if count % 10 == 0:
            print(f"Migrated {count}/{len(rows)} rows...")
    
    print(f"Successfully migrated {count} rows from {table_name} to {collection_name}.")
    return count

def migrate_all_tables():
    """Migrate all SQLite tables to Firebase"""
    # Get existing collections
    existing_collections = get_existing_collections()
    print(f"Existing Firebase collections: {existing_collections}")
    
    # Get SQLite tables
    sqlite_tables = get_sqlite_tables()
    print(f"SQLite tables: {sqlite_tables}")
    
    # Define table to collection mapping
    table_mapping = {
        'users': 'users',
        'categories': 'categories',
        'complaints': 'complaints',
        'complaint_updates': 'complaint_updates',
        'feedbacks': 'feedbacks',
        'audit_logs': 'audit_logs',
        'notifications': 'notifications',
        'official_requests': 'official_requests',
        'complaint_media': 'complaint_media'
    }
    
    # Migrate tables not already in Firebase
    total_migrated = 0
    for table, collection in table_mapping.items():
        if table in sqlite_tables and collection not in existing_collections:
            count = migrate_table_to_firebase(table, collection)
            total_migrated += count
    
    print(f"\nMigration complete! Migrated data for {total_migrated} records.")
    
    # Verify collections after migration
    new_collections = get_existing_collections()
    print(f"Firebase collections after migration: {new_collections}")

def main():
    """Main function to run the migration"""
    with app.app_context():
        # Initialize Firebase
        init_firebase()
        
        # Migrate all tables
        migrate_all_tables()

if __name__ == "__main__":
    print("This script will migrate all data from SQLite to Firebase.")
    print("Make sure your Firebase configuration is correct in the .env or config file.")
    print("This process may take some time depending on the amount of data.")
    
    confirm = input("Are you sure you want to proceed? (y/n): ")
    if confirm.lower() == 'y':
        print("Starting migration...")
        main()
    else:
        print("Migration cancelled.") 