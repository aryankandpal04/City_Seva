import random
import string
from datetime import datetime, timedelta
from flask import current_app
from app import firebase_auth

def generate_otp(length=6):
    """Generate a numeric OTP code"""
    return ''.join(random.choices(string.digits, k=length))

def store_otp(user_email, otp):
    """Store OTP in Firestore with expiration"""
    try:
        # Set expiration time (10 minutes)
        expiry = datetime.utcnow() + timedelta(minutes=10)
        
        # Convert to timestamp for Firestore
        expiry_timestamp = expiry.timestamp()
        
        # Store in Firestore
        firebase_auth.db.collection('otps').document(user_email).set({
            'code': otp,
            'expires_at': expiry_timestamp,
            'attempts': 0,
            'created_at': datetime.utcnow().timestamp()
        })
        
        current_app.logger.info(f"OTP stored for {user_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error storing OTP: {str(e)}")
        return False

def verify_otp_code(email, submitted_otp):
    """Verify submitted OTP against stored OTP"""
    try:
        otp_doc = firebase_auth.db.collection('otps').document(email).get()
        if not otp_doc.exists:
            current_app.logger.error(f"No OTP found for {email}")
            return False
        
        otp_data = otp_doc.to_dict()
        expiry_timestamp = otp_data.get('expires_at')
        stored_otp = otp_data.get('code')
        attempts = otp_data.get('attempts', 0)
        
        # Increment attempt counter
        firebase_auth.db.collection('otps').document(email).update({
            'attempts': attempts + 1
        })
        
        # Check if too many attempts (max 5)
        if attempts >= 5:
            current_app.logger.warning(f"Too many OTP attempts for {email}")
            return False
        
        # Check if OTP is expired
        if datetime.utcnow().timestamp() > expiry_timestamp:
            current_app.logger.warning(f"OTP expired for {email}")
            return False
            
        # Check if OTP matches
        is_match = stored_otp == submitted_otp
        if is_match:
            # Mark user as verified and clean up OTP
            user = firebase_auth.get_user_by_email(email)
            if user:
                firebase_auth.update_user(user.uid, email_verified=True)
                # Delete the used OTP
                firebase_auth.db.collection('otps').document(email).delete()
            
        return is_match
    except Exception as e:
        current_app.logger.error(f"Error verifying OTP: {str(e)}")
        return False

# Add a backward compatibility alias for code that might still use the old name
verify_otp = verify_otp_code

def send_otp_email(user, otp):
    """Send OTP via email"""
    from app.utils.email import send_email
    from flask import render_template
    
    try:
        # Get user display name
        name = getattr(user, 'display_name', None) or getattr(user, 'full_name', lambda: user.email.split('@')[0])
        if callable(name):
            name = name()
            
        current_app.logger.info(f"Sending OTP email to {user.email}")
        
        return send_email(
            subject='CitySeva Account Verification OTP',
            recipients=[user.email],
            text_body=render_template('email/otp_verification.txt', 
                                      name=name, otp=otp),
            html_body=render_template('email/otp_verification.html', 
                                      name=name, otp=otp)
        )
    except Exception as e:
        current_app.logger.error(f"Error sending OTP email: {str(e)}")
        return False 