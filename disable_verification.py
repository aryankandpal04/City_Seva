from app import create_app
from firebase_admin import auth
import os

def main():
    """Temporarily disable email verification in Firebase for testing"""
    app = create_app('development')
    
    with app.app_context():
        # Set environment variable to disable verification
        os.environ['REQUIRE_EMAIL_VERIFICATION'] = 'False'
        
        # Reload app configuration
        app.config['REQUIRE_EMAIL_VERIFICATION'] = False
        
        print("Email verification is now disabled in the environment.")
        print("To make this permanent, edit cityseva.env and set REQUIRE_EMAIL_VERIFICATION=False")
        
        # Also set up email if not already configured
        if not app.config.get('MAIL_USERNAME'):
            print("\nEmail is not configured. To enable email functionality:")
            print("1. Edit cityseva.env and add your email credentials:")
            print("   MAIL_USERNAME=your-email@gmail.com")
            print("   MAIL_PASSWORD=your-app-password")
            print("\nFor Gmail:")
            print("- Use an App Password (https://myaccount.google.com/apppasswords)")
            print("- Enable 2-Factor Authentication first")
            print("- Then generate an App Password for the application")
            
        print("\nRestart your Flask application for changes to take effect.")

if __name__ == "__main__":
    main() 