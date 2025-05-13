from flask import Flask
from app import create_app, db
from app.models import User
from datetime import datetime
import os

def update_admin():
    """Update or create admin user with specified credentials"""
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    
    with app.app_context():
        # Check if user exists
        email = 'admin123@gmail.com'
        password = 'Admin@123'
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update existing user
            user.password = password
            user.role = 'admin'
            db.session.commit()
            print(f"Updated existing admin user with email: {email}")
        else:
            # Create new admin user
            new_user = User(
                email=email,
                username=email.split('@')[0],
                first_name='Admin',
                last_name='User',
                role='admin',
                is_active=True,
                created_at=datetime.utcnow()
            )
            new_user.password = password
            db.session.add(new_user)
            db.session.commit()
            print(f"Created new admin user with email: {email}")
        
        print("Admin account has been updated successfully.")

if __name__ == '__main__':
    update_admin() 