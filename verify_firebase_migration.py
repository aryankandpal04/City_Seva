"""
Verify that the Firebase migration was successful.
This script checks that all necessary collections exist and tests core operations.
"""
import os
import sys
import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, firebase_db
from app.firebase_helpers import (
    get_categories, get_complaints, get_users,
    create_category, create_complaint, create_complaint_media,
    create_notification, create_audit_log, create_feedback,
    get_complaint_statistics
)

app = create_app('development')
with app.app_context():
    def check_firebase_initialized():
        """Check if Firebase is initialized"""
        print("Checking Firebase initialization...")
        
        # Check if Firebase Admin SDK is initialized
        if firebase_admin._apps:
            print("✅ Firebase Admin SDK is initialized")
            
            # Now check if our firebase_db wrapper is initialized
            if hasattr(firebase_db, 'db') and firebase_db.db is not None:
                print("✅ Firebase DB wrapper is initialized")
                return True
            else:
                print("❌ Firebase Admin SDK is initialized but our DB wrapper is not")
                # Initialize the DB wrapper
                firebase_db.db = firestore.client()
                print("✅ Firebase DB wrapper has been initialized")
                return True
        else:
            print("❌ Firebase Admin SDK is not initialized")
            return False
    
    def check_firebase_collections():
        """Check if all required collections exist"""
        print("\nChecking Firebase collections...")
        
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
        
        all_exist = True
        for collection_name in required_collections:
            try:
                # Try to get one document from the collection
                collection_ref = firebase_db.db.collection(collection_name)
                docs = list(collection_ref.limit(1).stream())
                
                if docs:
                    print(f"✅ Collection '{collection_name}' exists with {len(docs)} document(s)")
                else:
                    print(f"⚠️ Collection '{collection_name}' exists but is empty")
            except Exception as e:
                print(f"❌ Error checking collection '{collection_name}': {e}")
                all_exist = False
        
        return all_exist
    
    def test_basic_operations():
        """Test basic CRUD operations with Firebase"""
        print("\nTesting basic Firebase operations...")
        
        success = True
        test_data = {}
        
        try:
            # 1. Read operations
            print("\n1. Testing read operations...")
            
            # Get categories
            categories = get_categories()
            if categories:
                print(f"✅ Retrieved {len(categories)} categories")
                test_data['category_id'] = categories[0]['id']
            else:
                print("⚠️ No categories found")
                success = False
            
            # Get users
            users = get_users(limit=5)
            if users:
                print(f"✅ Retrieved {len(users)} users")
                test_data['user_id'] = users[0]['id']
            else:
                print("⚠️ No users found")
                success = False
            
            # Get complaints
            complaints = get_complaints(limit=5)
            if complaints:
                print(f"✅ Retrieved {len(complaints)} complaints")
            else:
                print("⚠️ No complaints found")
            
            # 2. Create operations
            print("\n2. Testing create operations...")
            
            if 'category_id' in test_data and 'user_id' in test_data:
                # Create a test complaint
                test_complaint = {
                    'title': 'Test Complaint (Migration Verification)',
                    'description': 'This is a test complaint created by the migration verification script',
                    'location': 'Test Location',
                    'latitude': 12.345,
                    'longitude': 67.890,
                    'category_id': test_data['category_id'],
                    'user_id': test_data['user_id'],
                    'status': 'pending',
                    'priority': 'medium'
                }
                
                new_complaint = create_complaint(test_complaint)
                if new_complaint and 'id' in new_complaint:
                    print(f"✅ Created test complaint with ID: {new_complaint['id']}")
                    test_data['complaint_id'] = new_complaint['id']
                    
                    # Create an audit log
                    audit_log = create_audit_log({
                        'user_id': test_data['user_id'],
                        'action': 'create_test',
                        'resource_type': 'complaint',
                        'resource_id': test_data['complaint_id'],
                        'details': 'Test audit log created by migration verification script',
                        'ip_address': '127.0.0.1'
                    })
                    if audit_log:
                        print("✅ Created audit log for test complaint")
                    else:
                        print("❌ Failed to create audit log")
                        success = False
                    
                    # Create a notification
                    notification = create_notification({
                        'user_id': test_data['user_id'],
                        'title': 'Test Notification',
                        'message': 'This is a test notification created by the migration verification script'
                    })
                    if notification and 'id' in notification:
                        print(f"✅ Created test notification with ID: {notification['id']}")
                    else:
                        print("❌ Failed to create notification")
                        success = False
                else:
                    print("❌ Failed to create test complaint")
                    success = False
            else:
                print("❌ Cannot create test complaint without category and user IDs")
                success = False
            
            # 3. Report generation
            print("\n3. Testing report generation...")
            
            stats = get_complaint_statistics()
            if stats:
                print("✅ Successfully generated complaint statistics:")
                print(f"  - Total complaints: {stats['status_counts']['total']}")
                print(f"  - Avg rating: {stats['avg_rating']}")
            else:
                print("❌ Failed to generate complaint statistics")
                success = False
            
            return success, test_data
            
        except Exception as e:
            print(f"❌ Error during basic operations test: {e}")
            return False, test_data
    
    def cleanup_test_data(test_data):
        """Clean up test data created during verification"""
        print("\nCleaning up test data...")
        
        if 'complaint_id' in test_data:
            try:
                # Delete the test complaint
                firebase_db.complaints_ref().document(test_data['complaint_id']).delete()
                print(f"✅ Deleted test complaint with ID: {test_data['complaint_id']}")
            except Exception as e:
                print(f"❌ Error deleting test complaint: {e}")
    
    # Run the verification
    print("Starting Firebase migration verification...")
    print("===========================================")
    
    if check_firebase_initialized():
        collections_valid = check_firebase_collections()
        if collections_valid:
            success, test_data = test_basic_operations()
            
            # Clean up test data
            if test_data:
                cleanup_test_data(test_data)
            
            if success:
                print("\n✅ All Firebase operations verified successfully!")
                print("\nMigration verification complete. Your app is ready to use Firebase as the primary data store.")
            else:
                print("\n⚠️ Some operations failed during verification.")
                print("Please check the error messages above and fix any issues before deploying.")
        else:
            print("\n⚠️ Not all required collections exist in Firebase.")
            print("Run the verify_firebase_collections.py script to create missing collections.")
    else:
        print("\n❌ Firebase is not initialized correctly. Please check your configuration.")
        print("Ensure your environment variables are set correctly and the service account key file exists.")

print("\nNext steps:")
print("1. If there were any issues, fix them and run this script again")
print("2. If everything passed, set USE_FIREBASE=True in your configuration")
print("3. Start your application and test all functionality") 