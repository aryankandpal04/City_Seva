from app import create_app
import firebase_admin
from firebase_admin import auth, credentials
import json
import os
import requests

def check_firebase_config():
    """Check if Firebase configuration is valid"""
    app = create_app('development')
    
    with app.app_context():
        print("==== Checking Firebase Configuration ====")
        
        # Check environment variables
        print("\nChecking Firebase environment variables:")
        required_vars = [
            'FIREBASE_API_KEY', 
            'FIREBASE_AUTH_DOMAIN', 
            'FIREBASE_PROJECT_ID', 
            'FIREBASE_STORAGE_BUCKET',
            'FIREBASE_MESSAGING_SENDER_ID',
            'FIREBASE_APP_ID'
        ]
        
        for var in required_vars:
            value = app.config.get(var)
            if value:
                print(f"✅ {var} is set: {value[:5]}{'*' * 10}")
            else:
                print(f"❌ {var} is not set")
        
        # Check service account key
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        print(f"\nService Account Key Path: {service_account_path}")
        
        if os.path.exists(service_account_path):
            print(f"✅ Service account file exists")
            try:
                with open(service_account_path, 'r') as f:
                    data = json.load(f)
                    if 'project_id' in data:
                        print(f"✅ Service account file is valid for project: {data['project_id']}")
                    else:
                        print(f"❌ Service account file is not valid - missing project_id")
            except Exception as e:
                print(f"❌ Error reading service account file: {e}")
        else:
            print(f"❌ Service account file does not exist at: {service_account_path}")
        
        # Verify Firebase is initialized
        print("\nChecking Firebase initialization:")
        try:
            # Check if we can get a auth listing
            page = auth.list_users(max_results=1)
            print(f"✅ Firebase is correctly initialized and can access user data")
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
        
        # Firebase Auth settings
        print("\n==== IMPORTANT STEPS TO ENABLE GOOGLE AUTH ====")
        print("1. Go to Firebase Console: https://console.firebase.google.com/")
        print(f"2. Select your project: {app.config.get('FIREBASE_PROJECT_ID')}")
        print("3. Go to Authentication > Sign-in method")
        print("4. Enable 'Google' as a provider")
        print("5. Add authorized domains:")
        print(f"   - Add '{app.config.get('FIREBASE_AUTH_DOMAIN')}'")
        print(f"   - Add 'localhost'")
        print("\nWith these settings, Google Sign-In should work correctly.")
        print("Note: You may need to restart your Flask application after enabling Google Auth")
        
if __name__ == '__main__':
    check_firebase_config() 