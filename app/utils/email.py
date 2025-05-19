from flask import render_template, current_app, url_for
from flask_mailman import EmailMessage as Message
from app import mail
from threading import Thread
import logging
import traceback

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            # Try to get connection information for debugging
            connection_info = f"Server: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}"
            connection_info += f", TLS: {app.config.get('MAIL_USE_TLS')}, Username: {app.config.get('MAIL_USERNAME')}"
            app.logger.info(f"Attempting to send email with: {connection_info}")
            
            # Send the message
            msg.send()
            app.logger.info(f"Email sent successfully to {msg.to}")
            return True
        except Exception as e:
            app.logger.error(f"Failed to send email via SMTP: {str(e)}")
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try fallback if available
            try:
                from app.utils.fallback_email import send_fallback_email, is_fallback_email_configured
                
                if is_fallback_email_configured():
                    app.logger.info(f"Attempting to send email via fallback API")
                    
                    # Get the recipients, could be a list or a string
                    to_emails = msg.to
                    if isinstance(to_emails, list):
                        to_email = to_emails[0]  # Send to first recipient
                    else:
                        to_email = to_emails
                    
                    # Try to send via fallback API
                    if send_fallback_email(
                        subject=msg.subject,
                        to_email=to_email,
                        html_content=msg.html,
                        text_content=msg.body
                    ):
                        app.logger.info(f"Email sent via fallback API to {to_email}")
                        return True
                    else:
                        app.logger.error("Fallback email sending failed too")
            except Exception as fallback_error:
                app.logger.error(f"Fallback email error: {str(fallback_error)}")
            
            # Both methods failed
            return False

def send_email(subject, recipients, text_body, html_body, sender=None):
    """Send an email"""
    try:
        if not sender:
            sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        current_app.logger.info(f"Preparing to send email '{subject}' to {recipients} from {sender}")
        
        # Create the message
        msg = Message(subject, to=recipients, from_email=sender)
        msg.body = text_body
        msg.html = html_body
        
        # Set content type for HTML explicitly
        msg.content_subtype = "html"
        
        # Set MIME headers to ensure HTML is prioritized
        msg.extra_headers = {
            'MIME-Version': '1.0',
            'Content-Type': 'text/html; charset=UTF-8'
        }
        
        # Threading variables to pass to child thread
        result = {"success": False}
        
        # Define a modified thread function that captures the result
        def send_with_result(app, msg, result_dict):
            result_dict["success"] = send_async_email(app, msg)
        
        # Send email asynchronously
        thread = Thread(
            target=send_with_result,
            args=(current_app._get_current_object(), msg, result)
        )
        thread.start()
        thread.join(timeout=5.0)  # Wait up to 5 seconds for the result
        
        # If thread is still running, it will continue in the background
        if thread.is_alive():
            current_app.logger.warning("Email thread is still running, continuing without waiting")
            return True
            
        return result["success"]
    except Exception as e:
        current_app.logger.error(f"Error preparing email: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def send_password_reset_email(user):
    """Send password reset email with OTP"""
    from app.utils.otp import generate_otp, store_otp
    
    # Generate OTP for password reset
    otp_code = generate_otp()
    
    # Store OTP in database
    store_otp(user.email, otp_code)
    
    # Get user display name
    name = getattr(user, 'display_name', None) or getattr(user, 'full_name', lambda: user.email.split('@')[0])
    if callable(name):
        name = name()
    
    send_email(
        subject='CitySeva Password Reset',
        recipients=[user.email],
        text_body=render_template('email/password_reset_otp.txt', 
                                 name=name, otp=otp_code),
        html_body=render_template('email/password_reset_otp.html', 
                                 name=name, otp=otp_code)
    )
    
    return otp_code

def send_email_verification(user, verification_link):
    """Send email verification link"""
    # Get user display name
    name = getattr(user, 'display_name', None) or getattr(user, 'full_name', lambda: user.email.split('@')[0])
    if callable(name):
        name = name()
    
    return send_email(
        subject='CitySeva Email Verification',
        recipients=[user.email],
        text_body=render_template('email/verify_email.txt', 
                                 name=name, verification_link=verification_link),
        html_body=render_template('email/verify_email.html', 
                                 name=name, verification_link=verification_link)
    )

def send_complaint_notification(complaint, category=None):
    """Send notification for new complaint"""
    from app.models import User
    
    try:
        # Skip if no department or category to determine recipients
        if not category and (not hasattr(complaint, 'category') or not complaint.category):
            current_app.logger.error("Cannot send notification: No category provided or associated with complaint")
            return False
        
        # Use provided category or get from complaint
        dept = None
        if category:
            dept = category.department
        elif hasattr(complaint, 'category') and hasattr(complaint.category, 'department'):
            dept = complaint.category.department
        
        if not dept:
            current_app.logger.error("Cannot send notification: No department associated with category")
            return False
        
        # Find officials in the relevant department
        officials = User.query.filter_by(role='official', department=dept).all()
        
        # Also notify admins
        admins = User.query.filter_by(role='admin').all()
        
        # Combine recipients
        recipients = officials + admins
        
        if not recipients:
            current_app.logger.error(f"No officials or admins found for department: {dept}")
            return False
        
        # Get complaint subject
        subject = getattr(complaint, 'subject', None) or getattr(complaint, 'title', 'New Complaint')
        
        # Send to each recipient
        sent_to_at_least_one = False
        for recipient in recipients:
            if not recipient.email:
                current_app.logger.warning(f"Skipping notification to user {recipient.id}: No email address")
                continue
                
            # Get recipient name for personalization
            recipient_name = getattr(recipient, 'display_name', None) or getattr(recipient, 'full_name', lambda: recipient.email.split('@')[0])
            if callable(recipient_name):
                recipient_name = recipient_name()
            
            success = send_email(
                subject=f'New Complaint: {subject}',
                recipients=[recipient.email],
                text_body=render_template('email/complaint_notification.txt', 
                                         complaint=complaint, recipient_name=recipient_name),
                html_body=render_template('email/complaint_notification.html', 
                                         complaint=complaint, recipient_name=recipient_name)
            )
            if success:
                sent_to_at_least_one = True
        
        return sent_to_at_least_one
    except Exception as e:
        current_app.logger.error(f"Error in send_complaint_notification: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return False

def send_contact_email(name, email, subject, message):
    """Send contact form submission email to admin."""
    try:
        return send_email(
            subject=f'New Contact Form Submission: {subject}',
            recipients=[current_app.config['ADMIN_EMAIL']],
            text_body=render_template('email/contact_email.txt',
                                     name=name,
                                     email=email,
                                     subject=subject,
                                     message=message),
            html_body=render_template('email/contact_email.html',
                                     name=name,
                                     email=email,
                                     subject=subject,
                                     message=message)
        )
    except Exception as e:
        current_app.logger.error(f"Error sending contact email: {str(e)}")
        return False 