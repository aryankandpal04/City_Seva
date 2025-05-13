from app import create_app
from firebase_admin import auth
from app import firebase_auth

def main():
    """Mark all existing Firebase users as email verified for testing"""
    # Create app with development config
    app = create_app('development')
    
    with app.app_context():
        try:
            print("Marking all users as email verified...")
            # Get the first batch of users (Firebase limits to 1000 per request)
            page = auth.list_users()
            
            verified_count = 0
            
            # Iterate through all users and mark as verified
            for user in page.users:
                try:
                    if not user.email_verified:
                        # Update the user in Firebase Auth
                        auth.update_user(user.uid, email_verified=True)
                        
                        # Also update in Firestore
                        firebase_auth.update_user(user.uid, email_verified=True)
                        
                        print(f"Verified email for: {user.email}")
                        verified_count += 1
                    else:
                        print(f"User {user.email} already verified")
                except Exception as e:
                    print(f"Error verifying {user.email}: {e}")
                    
            print(f"\nSuccessfully verified {verified_count} users.")
            print("All users should now be able to log in without email verification.")
            print("Restart your application to see the changes.")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main() 