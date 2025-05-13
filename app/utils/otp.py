import random
import string
from datetime import datetime, timedelta
from flask import current_app, session
from app import db

class OTP(db.Model):
    """OTP model for storing verification codes"""
    __tablename__ = 'otps'
    
    email = db.Column(db.String(120), primary_key=True)
    code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OTP {self.email}>'

def generate_otp(length=6):
    """Generate a numeric OTP code"""
    return ''.join(random.choices(string.digits, k=length))

def store_otp(user_email, otp):
    """Store OTP in database with expiration"""
    try:
        # Set expiration time (10 minutes)
        expiry = datetime.utcnow() + timedelta(minutes=current_app.config.get('OTP_EXPIRY_MINUTES', 10))
        
        # Check if OTP already exists
        existing_otp = OTP.query.filter_by(email=user_email).first()
        
        if existing_otp:
            # Update existing OTP
            existing_otp.code = otp
            existing_otp.expires_at = expiry
            existing_otp.attempts = 0
            existing_otp.created_at = datetime.utcnow()
        else:
            # Create new OTP
            new_otp = OTP(
                email=user_email,
                code=otp,
                expires_at=expiry,
                attempts=0,
                created_at=datetime.utcnow()
            )
            db.session.add(new_otp)
        
        db.session.commit()
        current_app.logger.info(f"OTP stored for {user_email}")
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error storing OTP: {str(e)}")
        return False

def verify_otp_code(email, submitted_otp):
    """Verify submitted OTP against stored OTP"""
    try:
        otp_record = OTP.query.filter_by(email=email).first()
        if not otp_record:
            current_app.logger.error(f"No OTP found for {email}")
            return False
        
        # Increment attempt counter
        otp_record.attempts += 1
        db.session.commit()
        
        # Check if too many attempts (max 5)
        max_attempts = current_app.config.get('OTP_MAX_ATTEMPTS', 5)
        if otp_record.attempts >= max_attempts:
            current_app.logger.warning(f"Too many OTP attempts for {email}")
            db.session.delete(otp_record)
            db.session.commit()
            return False
        
        # Check if OTP is expired
        if datetime.utcnow() > otp_record.expires_at:
            current_app.logger.warning(f"OTP expired for {email}")
            db.session.delete(otp_record)
            db.session.commit()
            return False
            
        # Check if OTP matches
        is_match = otp_record.code == submitted_otp
        if is_match:
            # Clean up OTP record to indicate verification is complete
            db.session.delete(otp_record)
            db.session.commit()
            
        return is_match
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error verifying OTP: {str(e)}")
        return False

# Add a backward compatibility alias for code that might still use the old name
verify_otp = verify_otp_code

def send_otp_email(user, otp):
    """Send OTP via email"""
    from app.utils.email import send_email
    from flask import render_template
    
    try:
        # Get user's name
        if hasattr(user, 'full_name'):
            name = user.full_name() 
        else:
            name = getattr(user, 'username', user.email.split('@')[0])
            
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