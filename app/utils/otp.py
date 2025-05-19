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
    from flask import render_template, render_template_string, current_app
    
    try:
        # Get user's name
        if hasattr(user, 'full_name'):
            name = user.full_name() 
        else:
            name = getattr(user, 'username', user.email.split('@')[0])
            
        current_app.logger.info(f"Sending OTP email to {user.email}")
        
        # Create HTML email content using template string
        html_content = render_template_string("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>CitySeva Account Verification</title>
        </head>
        <body bgcolor="#f0f8ff">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f0f8ff">
                <tr>
                    <td align="center" valign="top">
                        <table width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff">
                            <!-- Logo Header -->
                            <tr>
                                <td align="center" bgcolor="#f0f8ff" height="80">
                                    <table cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" valign="middle" bgcolor="#00bfff" width="60" height="60" style="border: 2px solid #0097a7;">
                                                <font color="#ffffff" size="5" face="Arial, sans-serif"><b>CS</b></font>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <!-- Header -->
                            <tr>
                                <td align="center" bgcolor="#00bfff" height="80">
                                    <font color="#ffffff" size="5" face="Arial, sans-serif"><b>CitySeva Email Verification</b></font>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td align="left" bgcolor="#ffffff" style="padding: 20px;">
                                    <font face="Arial, sans-serif" size="3" color="#333333">
                                        Hello <font color="#0097a7"><b>{{ name }}</b></font>,<br /><br />
                                        
                                        Thank you for registering with <font color="#00bfff"><b>CitySeva</b></font>. To verify your email address and activate your account, please use the verification code below:<br /><br />
                                    </font>
                                    
                                    <!-- OTP Box -->
                                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" height="100">
                                                <table cellpadding="0" cellspacing="0" border="0">
                                                    <tr>
                                                        <td align="center" bgcolor="#e0f7fa" style="padding: 15px 40px; border: 2px solid #00bfff;">
                                                            <font color="#0097a7" size="6" face="Arial, sans-serif"><b>{{ otp }}</b></font>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <table width="100%" cellpadding="10" cellspacing="0" border="0" bgcolor="#e1f5fe">
                                        <tr>
                                            <td align="center" bgcolor="#e1f5fe" style="border-left: 4px solid #00bfff;">
                                                <font color="#0288d1" size="2" face="Arial, sans-serif">This code will expire in <b>10 minutes</b>. Enter it on the verification page to complete your registration.</font>
                                            </td>
                                        </tr>
                                    </table>
                                    <br />
                                    
                                    <font face="Arial, sans-serif" size="3" color="#333333">
                                        If you didn't create an account with CitySeva, you can safely ignore this email.<br /><br />
                                    
                                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="border-top: 1px solid #e0f7fa; padding-top: 15px;">
                                                    <font color="#607d8b" size="3" face="Arial, sans-serif">
                                                        Best regards,<br />
                                                        <font color="#0097a7"><b>The CitySeva Team</b></font>
                                                    </font>
                                                </td>
                                            </tr>
                                        </table>
                                    </font>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td align="center" bgcolor="#e0f7fa" style="border-top: 3px solid #00bfff; padding: 15px;">
                                    <font color="#0288d1" size="2" face="Arial, sans-serif">Powered by CitySeva - Connecting Citizens & Government</font><br />
                                    <font color="#607d8b" size="2" face="Arial, sans-serif">This is an automated message. Please do not reply to this email.</font>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """, name=name, otp=otp)
        
        # Create text version of the email
        text_content = f"""
        CitySeva Email Verification
        
        Hello {name},
        
        Thank you for registering with CitySeva. To verify your email address and activate your account, please use the verification code below:
        
        {otp}
        
        This code will expire in 10 minutes. Enter it on the verification page to complete your registration.
        
        If you didn't create an account with CitySeva, you can safely ignore this email.
        
        Best regards,
        The CitySeva Team
        """
        
        return send_email(
            subject='CitySeva Account Verification OTP',
            recipients=[user.email],
            text_body=text_content,
            html_body=html_content
        )
    except Exception as e:
        current_app.logger.error(f"Error sending OTP email: {str(e)}")
        return False 