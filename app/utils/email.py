from flask import render_template, render_template_string, current_app, url_for
from flask_mailman import EmailMessage as Message
from app import mail
from threading import Thread
import logging
import traceback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            # Try to get connection information for debugging
            connection_info = f"Server: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}"
            connection_info += f", TLS: {app.config.get('MAIL_USE_TLS')}, Username: {app.config.get('MAIL_USERNAME')}"
            app.logger.info(f"Attempting to send email with: {connection_info}")
            
            # Send the message using direct SMTP connection
            smtp_server = app.config.get('MAIL_SERVER')
            smtp_port = app.config.get('MAIL_PORT')
            smtp_username = app.config.get('MAIL_USERNAME')
            smtp_password = app.config.get('MAIL_PASSWORD')
            use_tls = app.config.get('MAIL_USE_TLS', False)
            use_ssl = app.config.get('MAIL_USE_SSL', False)
            
            # Create SMTP connection
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if use_tls:
                    server.starttls()
            
            # Login if credentials provided
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            
            # Send the email
            server.send_message(msg)
            server.quit()
            
            app.logger.info(f"Email sent successfully to {msg['To']}")
            return True
        except Exception as e:
            app.logger.error(f"Failed to send email via SMTP: {str(e)}")
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try fallback if available
            try:
                from app.utils.fallback_email import send_fallback_email, is_fallback_email_configured
                
                if is_fallback_email_configured():
                    app.logger.info(f"Attempting to send email via fallback API")
                    
                    # Get the recipient from the message
                    to_emails = msg['To']
                    
                    # Try to send via fallback API
                    if send_fallback_email(
                        subject=msg['Subject'],
                        to_email=to_emails,
                        html_content=msg.get_payload(1).get_payload(),
                        text_content=msg.get_payload(0).get_payload()
                    ):
                        app.logger.info(f"Email sent via fallback API to {to_emails}")
                        return True
                    else:
                        app.logger.error("Fallback email sending failed too")
            except Exception as fallback_error:
                app.logger.error(f"Fallback email error: {str(fallback_error)}")
            
            # Both methods failed
            return False

def send_email(subject, recipients, text_body, html_body, sender=None):
    """Send an email using native MIME formatting instead of flask_mailman"""
    try:
        if not sender:
            sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        current_app.logger.info(f"Preparing to send email '{subject}' to {recipients} from {sender}")
        
        # Create the message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        
        # Handle recipient(s)
        if isinstance(recipients, list):
            msg['To'] = ', '.join(recipients)
        else:
            msg['To'] = recipients
        
        # Attach text part (this is the fallback)
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Attach HTML part (this is what will display if email client supports it)
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Add important headers for MIME handling
        msg['MIME-Version'] = '1.0'
        
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
    
    # Create HTML email content using template string
    html_content = render_template_string("""
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>CitySeva Password Reset</title>
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
                                <font color="#ffffff" size="5" face="Arial, sans-serif"><b>CitySeva Password Reset</b></font>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td align="left" bgcolor="#ffffff" style="padding: 20px;">
                                <font face="Arial, sans-serif" size="3" color="#333333">
                                    Hello <font color="#0097a7"><b>{{ name }}</b></font>,<br /><br />
                                    
                                    You requested to reset your password for your <font color="#00bfff"><b>CitySeva</b></font> account. Please use the verification code below to complete the process:<br /><br />
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
                                            <font color="#0288d1" size="2" face="Arial, sans-serif">This code will expire in <b>10 minutes</b>. Enter it on the password reset page to set a new password.</font>
                                        </td>
                                    </tr>
                                </table>
                                <br />
                                <font face="Arial, sans-serif" size="3" color="#333333">
                                    If you didn't request a password reset, please ignore this email or contact support if you have concerns about your account security.<br /><br />
                                
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
    """, name=name, otp=otp_code)
    
    # Create text version of the email
    text_content = f"""
    CitySeva Password Reset
    
    Hello {name},
    
    You requested to reset your password for your CitySeva account. Please use the verification code below to complete the process:
    
    {otp_code}
    
    This code will expire in 10 minutes. Enter it on the password reset page to set a new password.
    
    If you didn't request a password reset, please ignore this email or contact support if you have concerns about your account security.
    
    Best regards,
    The CitySeva Team
    """
    
    send_email(
        subject='CitySeva Password Reset',
        recipients=[user.email],
        text_body=text_content,
        html_body=html_content
    )
    
    return otp_code

def send_email_verification(user, verification_link):
    """Send email verification link"""
    # Get user display name
    name = getattr(user, 'display_name', None) or getattr(user, 'full_name', lambda: user.email.split('@')[0])
    if callable(name):
        name = name()
    
    # Create HTML email content using template string
    html_content = render_template_string("""
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>CitySeva Email Verification</title>
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
                                    
                                    Thank you for registering with <font color="#00bfff"><b>CitySeva</b></font>. To verify your email address and activate your account, please click the button below:<br /><br />
                                </font>
                                
                                <!-- Verification Button -->
                                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                    <tr>
                                        <td align="center" height="60">
                                            <table cellpadding="0" cellspacing="0" border="0">
                                                <tr>
                                                    <td align="center" bgcolor="#00bfff" style="padding: 10px 30px; border: 2px solid #0097a7;">
                                                        <a href="{{ verification_link }}" style="text-decoration: none;">
                                                            <font color="#ffffff" size="3" face="Arial, sans-serif"><b>Verify Email Address</b></font>
                                                        </a>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                                <br />
                                
                                <table width="100%" cellpadding="10" cellspacing="0" border="0" bgcolor="#e1f5fe">
                                    <tr>
                                        <td align="center" bgcolor="#e1f5fe" style="border-left: 4px solid #00bfff;">
                                            <font color="#0288d1" size="2" face="Arial, sans-serif">If the button doesn't work, copy and paste this link into your browser:</font><br />
                                            <font color="#607d8b" size="2" face="Arial, sans-serif">{{ verification_link }}</font>
                                        </td>
                                    </tr>
                                </table>
                                <br />
                                
                                <table width="100%" cellpadding="10" cellspacing="0" border="0" bgcolor="#e3f2fd">
                                    <tr>
                                        <td bgcolor="#e3f2fd" style="border-left: 4px solid #2196f3;">
                                            <font color="#1565c0" size="2" face="Arial, sans-serif"><b>Note:</b> This link will expire in 24 hours for security reasons.</font>
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
    """, name=name, verification_link=verification_link)
    
    # Create text version of the email
    text_content = f"""
    CitySeva Email Verification
    
    Hello {name},
    
    Thank you for registering with CitySeva. To verify your email address and activate your account, please click the link below:
    
    {verification_link}
    
    This link will expire in 24 hours for security reasons.
    
    If you didn't create an account with CitySeva, you can safely ignore this email.
    
    Best regards,
    The CitySeva Team
    """
    
    return send_email(
        subject='CitySeva Email Verification',
        recipients=[user.email],
        text_body=text_content,
        html_body=html_content
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