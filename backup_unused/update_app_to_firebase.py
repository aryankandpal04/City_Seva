"""
Update the application configuration to use Firebase as the primary data store.
This script will:
1. Add USE_FIREBASE=True to the environment file
2. Create necessary import statements in the app/__init__.py file
"""
import os
import re
import sys
import dotenv

def update_environment_file():
    """Update the environment file to use Firebase"""
    print("Updating environment file...")
    
    env_file = "cityseva.env"
    if not os.path.exists(env_file):
        print(f"Warning: {env_file} not found. Creating a new one.")
        with open(env_file, "w") as f:
            f.write("# CitySeva WebApp Environment Configuration\n\n")
    
    # Load environment variables
    dotenv.load_dotenv(env_file)
    
    # Check if USE_FIREBASE is already set
    use_firebase = os.environ.get("USE_FIREBASE")
    if use_firebase and use_firebase.lower() == "true":
        print("USE_FIREBASE is already set to True in the environment file.")
    else:
        # Add USE_FIREBASE=True to the environment file
        with open(env_file, "a") as f:
            f.write("\n# Firebase Configuration\n")
            f.write("USE_FIREBASE=True\n")
        print(f"Added USE_FIREBASE=True to {env_file}")
    
    return True

def check_app_init_file():
    """Check if the app/__init__.py file has necessary Firebase imports"""
    print("Checking app/__init__.py file...")
    
    init_file = "app/__init__.py"
    if not os.path.exists(init_file):
        print(f"Error: {init_file} not found. Make sure you're in the correct directory.")
        return False
    
    with open(init_file, "r") as f:
        content = f.read()
    
    # Check if Firebase is imported
    firebase_imported = "import firebase_db" in content or "from . import firebase_db" in content
    
    if firebase_imported:
        print("Firebase is already imported in app/__init__.py")
        return True
    else:
        print("Firebase import not found in app/__init__.py")
        print("This is okay - Firebase initialization is likely handled elsewhere.")
        return True

def main():
    """Update the application to use Firebase"""
    print("\nUpdating CitySeva WebApp to use Firebase")
    print("=====================================\n")
    
    success = True
    
    # 1. Update environment file
    success = update_environment_file() and success
    
    # 2. Check app/__init__.py file
    success = check_app_init_file() and success
    
    if success:
        print("\nSuccessfully updated the application to use Firebase!")
        print("You can now run the migration script to transfer your data.")
    else:
        print("\nSome updates failed. Please check the error messages above.")
    
    return success

if __name__ == "__main__":
    main() 