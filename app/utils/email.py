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
            
            # Try Firebase fallback if available
            try:
                from app.utils.firebase_email import send_firebase_email, is_firebase_email_configured
                
                if is_firebase_email_configured():
                    app.logger.info(f"Attempting to send email via Firebase fallback")
                    
                    # Get the recipients, could be a list or a string
                    to_emails = msg.to
                    if isinstance(to_emails, list):
                        to_email = to_emails[0]  # Send to first recipient
                    else:
                        to_email = to_emails
                    
                    # Try to send via Firebase
                    if send_firebase_email(
                        subject=msg.subject,
                        to_email=to_email,
                        html_content=msg.html,
                        text_content=msg.body
                    ):
                        app.logger.info(f"Email sent via Firebase to {to_email}")
                        return True
                    else:
                        app.logger.error("Firebase email sending failed too")
            except Exception as firebase_error:
                app.logger.error(f"Firebase email error: {str(firebase_error)}")
            
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

def send_password_reset_email(user, reset_link):
    """Send password reset email"""
    # Ensure reset_link is a full URL
    if not reset_link.startswith('http'):
        reset_link = f"{current_app.config['BASE_URL']}/reset_password/{reset_link}"
    
    # Get user display name
    name = getattr(user, 'display_name', None) or getattr(user, 'full_name', lambda: user.email.split('@')[0])
    if callable(name):
        name = name()
    
    send_email(
        subject='CitySeva Password Reset',
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', 
                                 name=name, reset_url=reset_link),
        html_body=render_template('email/reset_password.html', 
                                 name=name, reset_url=reset_link)
    )

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

def send_complaint_notification(complaint):
    """Send notification for new complaint"""
    # Skip if no recipient
    if not hasattr(complaint, 'assigned_to') or not complaint.assigned_to or not complaint.assigned_to.email:
        return
    
    # Get recipient name for personalization
    recipient_name = getattr(complaint.assigned_to, 'display_name', None) or getattr(complaint.assigned_to, 'full_name', lambda: complaint.assigned_to.email.split('@')[0])
    if callable(recipient_name):
        recipient_name = recipient_name()
    
    # Get complaint subject
    subject = getattr(complaint, 'subject', None) or getattr(complaint, 'title', 'New Complaint')
    
    send_email(
        subject=f'New Complaint: {subject}',
        recipients=[complaint.assigned_to.email],
        text_body=render_template('email/complaint_notification.txt', 
                                 complaint=complaint, recipient_name=recipient_name),
        html_body=render_template('email/complaint_notification.html', 
                                 complaint=complaint, recipient_name=recipient_name)
    ) 