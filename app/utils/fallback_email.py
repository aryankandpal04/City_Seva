"""
Email sending via external API as a fallback
This provides a fallback method to send emails when SMTP fails
"""
import requests
import json
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def send_fallback_email(subject, to_email, html_content, text_content=None):
    """
    Send an email using an external API service
    
    This can be configured to use services like SendGrid, Mailgun, etc.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get the API URL from config
        api_url = current_app.config.get('FALLBACK_EMAIL_API_URL')
        api_key = current_app.config.get('FALLBACK_EMAIL_API_KEY')
        
        if not api_url:
            logger.warning("Fallback email API URL not configured")
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
            headers["Authorization"] = f"Bearer {api_key}"
            
        # Make the request to the API service
        response = requests.post(
            api_url,
            data=json.dumps(data),
            headers=headers,
            timeout=10
        )
        
        # Check if successful
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                logger.info(f"Email sent via fallback API to {to_email}")
                return True
                
        logger.error(f"Failed to send email via fallback API: {response.text}")
        return False
        
    except Exception as e:
        logger.error(f"Error sending email via fallback API: {str(e)}")
        return False
        
def is_fallback_email_configured():
    """Check if fallback email sending is configured"""
    return bool(current_app.config.get('FALLBACK_EMAIL_API_URL')) 