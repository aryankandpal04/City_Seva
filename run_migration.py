"""
Run the complete Firebase migration process in a single script.
This script orchestrates all migration steps in the correct order.
"""
import os
import sys
import subprocess
import shutil
import time
import dotenv

def print_step(step_number, step_description):
    """Print a formatted step header"""
    print("\n" + "=" * 80)
    print(f"STEP {step_number}: {step_description}")
    print("=" * 80 + "\n")

def run_command(command, description=None):
    """Run a command and return success/failure"""
    if description:
        print(f"Running: {description}")
    print(f"$ {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        return False

def backup_database():
    """Backup the SQLite database"""
    print("Backing up SQLite database...")
    
    if os.path.exists("instance/cityseva.db"):
        # Create backups directory if it doesn't exist
        os.makedirs("backups", exist_ok=True)
        
        # Create a timestamped backup
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/cityseva.db.{timestamp}"
        
        shutil.copy2("instance/cityseva.db", backup_path)
        print(f"Database backed up to: {backup_path}")
        return True
    else:
        print("Warning: SQLite database not found at instance/cityseva.db")
        return False

def install_dependencies():
    """Install required dependencies"""
    return run_command("pip install -r requirements-firebase.txt", 
                      "Installing Firebase dependencies")

def check_firebase_configuration():
    """Check if Firebase configuration is properly set up"""
    print("Checking Firebase configuration...")
    
    # Load .env file if it exists
    if os.path.exists("cityseva.env"):
        dotenv.load_dotenv("cityseva.env")
    
    # Check required environment variables
    required_vars = [
        'FIREBASE_API_KEY',
        'FIREBASE_AUTH_DOMAIN',
        'FIREBASE_PROJECT_ID',
        'FIREBASE_STORAGE_BUCKET',
        'FIREBASE_SERVICE_ACCOUNT_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: The following required Firebase environment variables are missing:")
        for var in missing_vars:
            print(f"  - {var}")
        
        print("\nPlease add these to your cityseva.env file before continuing.")
        return False
    
    # Check if service account key file exists
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    if not os.path.exists(service_account_path):
        print(f"Error: Firebase service account key file not found at {service_account_path}")
        return False
    
    print("Firebase configuration looks good!")
    return True

def update_app_configuration():
    """Update app configuration to use Firebase"""
    return run_command("python update_app_to_firebase.py",
                      "Updating app configuration to use Firebase")

def verify_firebase_collections():
    """Verify Firebase collections exist"""
    return run_command("python verify_firebase_collections.py",
                      "Verifying Firebase collections")

def run_migration():
    """Run the actual migration script"""
    return run_command("python migrate_to_firebase.py",
                      "Migrating data from SQLite to Firebase")

def verify_migration():
    """Verify the migration was successful"""
    return run_command("python verify_firebase_migration.py",
                      "Verifying migration success")

def main():
    """Run the complete migration process"""
    print("\nCitySeva WebApp Firebase Migration")
    print("==================================\n")
    
    print("This script will migrate all data from SQLite to Firebase.")
    print("Make sure your Firebase configuration is correctly set up in cityseva.env\n")
    
    # Confirm before proceeding
    confirm = input("Are you sure you want to proceed with the migration? (y/n): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return
    
    # Step 1: Check Firebase configuration
    print_step(1, "Checking Firebase configuration")
    if not check_firebase_configuration():
        print("Migration aborted due to missing Firebase configuration.")
        return
    
    # Step 2: Backup database
    print_step(2, "Backing up SQLite database")
    if not backup_database():
        if input("Continue without backup? (y/n): ").lower() != 'y':
            print("Migration aborted.")
            return
    
    # Step 3: Install dependencies
    print_step(3, "Installing dependencies")
    if not install_dependencies():
        if input("Continue despite dependency installation failure? (y/n): ").lower() != 'y':
            print("Migration aborted.")
            return
    
    # Step 4: Verify Firebase collections
    print_step(4, "Verifying Firebase collections")
    if not verify_firebase_collections():
        if input("Continue despite Firebase collection verification failure? (y/n): ").lower() != 'y':
            print("Migration aborted.")
            return
    
    # Step 5: Run migration
    print_step(5, "Running migration")
    if not run_migration():
        print("Migration failed. Please check the error messages above.")
        return
    
    # Step 6: Verify migration
    print_step(6, "Verifying migration success")
    verify_migration() # We continue even if verification fails
    
    # All done!
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print("\nThe migration process has completed.")
    print("\nNext steps:")
    print("1. Check the Firebase console to verify your data")
    print("2. Test your application to ensure it works correctly with Firebase")
    print("3. Update your production environment to use Firebase")
    
    print("\nTo revert to SQLite temporarily, set USE_FIREBASE=False in your environment variables.")

if __name__ == "__main__":
    main() 