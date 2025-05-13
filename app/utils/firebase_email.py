"""
Email sending via Firebase Cloud Functions
This provides a fallback method to send emails when SMTP fails
"""
import requests
import json
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def send_firebase_email(subject, to_email, html_content, text_content=None):
    """
    Send an email using Firebase Cloud Functions
    
    This requires deploying a Cloud Function to Firebase with email sending capabilities.
    The function is not included in this app but can be created separately with:
    - Firebase Authentication
    - Firebase Cloud Functions
    - A service like SendGrid, Mailgun, etc.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get the Firebase function URL from config (if available)
        function_url = current_app.config.get('FIREBASE_EMAIL_FUNCTION_URL')
        api_key = current_app.config.get('FIREBASE_EMAIL_API_KEY')
        
        if not function_url:
            logger.warning("Firebase email function URL not configured")
            return False
            
        # Prepare the request data
        data = {
            "subject": subject,
            "to": to_email,
            "html": html_content
        }
        
        if text_content:
            data["text"] = text_content
            
        # Add API key for security if available
        headers = {
            "Content-Type": "application/json"
        }
        
        if api_key:
            headers["X-API-Key"] = api_key
            
        # Make the request to the Firebase function
        response = requests.post(
            function_url,
            data=json.dumps(data),
            headers=headers,
            timeout=10
        )
        
        # Check if successful
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                logger.info(f"Email sent via Firebase function to {to_email}")
                return True
                
        logger.error(f"Failed to send email via Firebase: {response.text}")
        return False
        
    except Exception as e:
        logger.error(f"Error sending email via Firebase: {str(e)}")
        return False
        
def is_firebase_email_configured():
    """Check if Firebase email sending is configured"""
    return bool(current_app.config.get('FIREBASE_EMAIL_FUNCTION_URL')) 