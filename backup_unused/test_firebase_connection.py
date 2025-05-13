"""
Test Firebase connection and initialization.
This script helps diagnose Firebase connection issues without running the full migration.
"""
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore
import dotenv

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_firebase_connection():
    """Test connection to Firebase"""
    print("Testing Firebase connection...")
    
    # Load environment variables
    if os.path.exists("cityseva.env"):
        dotenv.load_dotenv("cityseva.env")
        print("Loaded environment from cityseva.env")
    
    # Check for Firebase service account key
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    if not service_account_path:
        print("Error: FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set")
        return False
    
    if not os.path.exists(service_account_path):
        print(f"Error: Service account key file not found at {service_account_path}")
        return False
    
    print(f"Found service account key at {service_account_path}")
    
    try:
        # Initialize Firebase with a unique name for testing
        if not firebase_admin._apps:
            print("Initializing Firebase Admin SDK...")
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, name='test_connection')
            print("Firebase Admin SDK initialized successfully")
        else:
            print("Firebase Admin SDK already initialized")
            
            # Check if our test app exists
            if 'test_connection' not in firebase_admin._apps:
                print("Initializing test connection app...")
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, name='test_connection')
                print("Test connection app initialized")
        
        # Test Firestore connection
        print("Testing Firestore connection...")
        db = firestore.client(app=firebase_admin.get_app(name='test_connection'))
        
        # Try a simple query
        collections = db.collections()
        collection_names = [collection.id for collection in collections]
        
        print(f"Successfully connected to Firestore!")
        print(f"Available collections: {', '.join(collection_names) if collection_names else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"Error connecting to Firebase: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Firebase Connection Test")
    print("=======================\n")
    
    success = test_firebase_connection()
    
    if success:
        print("\n✅ Firebase connection test passed!")
        print("You can now safely run the migration process.")
    else:
        print("\n❌ Firebase connection test failed.")
        print("Please check your Firebase configuration before running the migration.") 