from datetime import datetime
from flask import current_app
from app import db
from app.models import Notification, User

def send_notification(user_id, title, message):
    """
    Send an in-app notification to a specific user
    
    Args:
        user_id: The ID of the user to send the notification to
        title: The notification title
        message: The notification message
        
    Returns:
        True if notification was created successfully, False otherwise
    """
    try:
        # Create notification
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(notification)
        db.session.commit()
        
        current_app.logger.info(f"Notification sent to user {user_id}: {title}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending notification: {str(e)}")
        db.session.rollback()
        return False

def send_notification_to_role(role, title, message):
    """
    Send the same notification to all users with a specific role
    
    Args:
        role: The role of users to send notifications to (e.g., 'admin', 'official')
        title: The notification title
        message: The notification message
        
    Returns:
        Number of users notified successfully
    """
    try:
        users = User.query.filter_by(role=role).all()
        count = 0
        
        for user in users:
            if send_notification(user.id, title, message):
                count += 1
                
        current_app.logger.info(f"Sent notifications to {count} users with role '{role}'")
        return count
    except Exception as e:
        current_app.logger.error(f"Error sending notifications to role {role}: {str(e)}")
        return 0

def send_notification_to_department(department, title, message):
    """
    Send the same notification to all officials in a specific department
    
    Args:
        department: The department name
        title: The notification title
        message: The notification message
        
    Returns:
        Number of users notified successfully
    """
    try:
        officials = User.query.filter_by(role='official', department=department).all()
        count = 0
        
        for official in officials:
            if send_notification(official.id, title, message):
                count += 1
                
        current_app.logger.info(f"Sent notifications to {count} officials in department '{department}'")
        return count
    except Exception as e:
        current_app.logger.error(f"Error sending notifications to department {department}: {str(e)}")
        return 0

def send_complaint_notification_in_app(complaint):
    """
    Send in-app notifications about a new complaint to relevant officials and admins
    
    Args:
        complaint: The Complaint object
        
    Returns:
        Number of users notified
    """
    try:
        if not complaint or not hasattr(complaint, 'category') or not complaint.category:
            current_app.logger.error("Cannot send notification: No category or complaint")
            return 0
            
        department = complaint.category.department
        if not department:
            current_app.logger.error("Cannot send notification: No department for category")
            return 0
        
        # Notification content
        title = f"New Complaint: #{complaint.id}"
        message = f"A new complaint has been submitted in the {complaint.category.name} category that requires your attention."
        
        # Send to officials in the relevant department
        dept_count = send_notification_to_department(department, title, message)
        
        # Also notify admins
        admin_count = send_notification_to_role('admin', title, message)
        
        return dept_count + admin_count
    except Exception as e:
        current_app.logger.error(f"Error sending in-app complaint notification: {str(e)}")
        return 0

def mark_notifications_as_read(user_id):
    """
    Mark all unread notifications for a user as read
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Number of notifications marked as read
    """
    try:
        unread = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        count = len(unread)
        
        for notification in unread:
            notification.is_read = True
            
        db.session.commit()
        current_app.logger.info(f"Marked {count} notifications as read for user {user_id}")
        return count
    except Exception as e:
        current_app.logger.error(f"Error marking notifications as read: {str(e)}")
        db.session.rollback()
        return 0 