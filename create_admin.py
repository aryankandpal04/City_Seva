from app import create_app
from app.firebase_auth import create_user, update_user

def main():
    # Create app with development config
    app = create_app('development')
    
    with app.app_context():
        try:
            print('Creating admin user...')
            # Create the user
            user = create_user(
                email='admin123@gmail.com',
                password='Admin@123',
                display_name='Admin User'
            )
            print(f'User created with UID: {user.uid}')
            
            # Update the user role to admin
            update_user(user.uid, role='admin')
            print('User role updated to admin')
            print('Admin user created successfully!')
        except Exception as e:
            print(f'Error creating admin user: {str(e)}')

if __name__ == '__main__':
    main() 