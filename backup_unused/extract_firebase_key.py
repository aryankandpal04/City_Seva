#!/usr/bin/env python
"""
Script to help extract Firebase credentials from the existing Flask app config.
This can be used to get the service account key for creating collections.
"""
import os
import json
import sys
from flask import Flask

# Define the target key file name
TARGET_KEY_FILE = 'cityseva-4d82b-firebase-adminsdk-fbsvc-a904038f62.json'

def extract_firebase_key():
    """Extract Firebase key from the Flask app configuration"""
    try:
        # Create a temporary Flask app to access config
        app = Flask(__name__)
        
        # Load config from environment variable
        app.config.from_object(os.environ.get('FLASK_CONFIG') or 'config.DevelopmentConfig')
        
        # Check if specified key file already exists
        if os.path.exists(TARGET_KEY_FILE):
            print(f"✅ Firebase key file '{TARGET_KEY_FILE}' already exists!")
            print("   You can use this key file with create_collections.py")
            return True
        
        # Check if FIREBASE_CREDENTIALS is in the config
        if hasattr(app.config, 'FIREBASE_CREDENTIALS') and app.config['FIREBASE_CREDENTIALS']:
            creds = app.config['FIREBASE_CREDENTIALS']
            
            # Create the key file
            with open(TARGET_KEY_FILE, 'w') as f:
                json.dump(creds, f, indent=2)
            
            print(f"✅ Firebase key extracted and saved to {TARGET_KEY_FILE}")
            print("   You can now use this key file with create_collections.py")
            return True
            
        # Check if FIREBASE_KEY_FILE is in the config
        elif hasattr(app.config, 'FIREBASE_KEY_FILE') and app.config['FIREBASE_KEY_FILE']:
            key_file = app.config['FIREBASE_KEY_FILE']
            
            if os.path.exists(key_file):
                # Create a copy of the key file
                with open(key_file, 'r') as src:
                    with open(TARGET_KEY_FILE, 'w') as dest:
                        dest.write(src.read())
                
                print(f"✅ Firebase key copied from {key_file} to {TARGET_KEY_FILE}")
                print("   You can now use this key file with create_collections.py")
                return True
            else:
                print(f"⚠️ Firebase key file {key_file} not found!")
                
        else:
            # Check common locations for Firebase key
            possible_locations = [
                TARGET_KEY_FILE,
                'firebase-key.json',
                'firebase-admin-key.json',
                'firebase-credentials.json',
                'instance/firebase-key.json',
                os.path.join('instance', 'firebase-key.json')
            ]
            
            for location in possible_locations:
                if os.path.exists(location):
                    print(f"✅ Found Firebase key at {location}")
                    
                    # If not already the target file, copy it
                    if location != TARGET_KEY_FILE:
                        with open(location, 'r') as src:
                            with open(TARGET_KEY_FILE, 'w') as dest:
                                dest.write(src.read())
                        print(f"✅ Copied key to {TARGET_KEY_FILE} for use with create_collections.py")
                    else:
                        print(f"   You can use this key file with create_collections.py")
                    
                    return True
            
            # Check environment variables
            if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                key_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                
                if os.path.exists(key_file):
                    with open(key_file, 'r') as src:
                        with open(TARGET_KEY_FILE, 'w') as dest:
                            dest.write(src.read())
                    
                    print(f"✅ Firebase key copied from {key_file} to {TARGET_KEY_FILE}")
                    print("   You can now use this key file with create_collections.py")
                    return True
            
            print("❌ Could not find Firebase credentials in config!")
            print("\nPlease ensure you have Firebase credentials set up in one of these ways:")
            print("1. A FIREBASE_CREDENTIALS dictionary in your Flask config")
            print("2. A FIREBASE_KEY_FILE path in your Flask config")
            print(f"3. A {TARGET_KEY_FILE} file in your project root")
            print("4. The GOOGLE_APPLICATION_CREDENTIALS environment variable set")
            
            return False
            
    except Exception as e:
        print(f"Error extracting Firebase key: {str(e)}")
        return False

if __name__ == "__main__":
    if not extract_firebase_key():
        print("\nManual solution:")
        print("1. Go to Firebase Console (https://console.firebase.google.com)")
        print("2. Select your project")
        print("3. Go to Project Settings > Service accounts")
        print("4. Click 'Generate new private key'")
        print(f"5. Save the downloaded file as '{TARGET_KEY_FILE}' in this directory")
        sys.exit(1) 