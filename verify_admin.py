from app import create_app
from app.firebase_auth import update_user
from firebase_admin import auth

def main():
    # Create app with development config
    app = create_app('development')
    
    with app.app_context():
        try:
            admin_email = 'admin123@gmail.com'
            print(f'Verifying email for admin user: {admin_email}')
            
            # Get the user from Firebase Auth
            user = auth.get_user_by_email(admin_email)
            print(f'Found user with UID: {user.uid}')
            
            # Update the user's email_verified status in Firebase Auth
            auth.update_user(user.uid, email_verified=True)
            
            # Also update in Firestore if needed
            update_user(user.uid, email_verified=True)
            
            print('Admin user email verified successfully!')
        except Exception as e:
            print(f'Error verifying admin user email: {str(e)}')

if __name__ == '__main__':
    main() 