from flask import render_template, current_app, url_for
from flask_mailman import EmailMessage
from app import mail
from threading import Thread

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, html_body, text_body=None):
    """Send email with the given details"""
    msg = EmailMessage(
        subject=subject,
        body=text_body or html_body,
        to=recipients,
        html_message=html_body
    )
    
    # Send email asynchronously
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()

def send_password_reset_email(user):
    """Send password reset email to user"""
    token = user.generate_reset_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    html_body = render_template(
        'email/reset_password.html',
        user=user,
        reset_url=reset_url
    )
    
    text_body = render_template(
        'email/reset_password.txt',
        user=user,
        reset_url=reset_url
    )
    
    send_email(
        subject='CitySeva - Reset Your Password',
        recipients=[user.email],
        html_body=html_body,
        text_body=text_body
    )

def send_complaint_notification(user, complaint, status_change=None):
    """Send notification about complaint status change"""
    html_body = render_template(
        'email/complaint_notification.html',
        user=user,
        complaint=complaint,
        status_change=status_change
    )
    
    text_body = render_template(
        'email/complaint_notification.txt',
        user=user,
        complaint=complaint,
        status_change=status_change
    )
    
    send_email(
        subject=f'CitySeva - Complaint #{complaint.id} Update',
        recipients=[user.email],
        html_body=html_body,
        text_body=text_body
    ) 