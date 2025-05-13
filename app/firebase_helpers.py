"""
Helper functions for using Firebase as the primary database for CitySeva WebApp.
This module provides a layer of abstraction over Firebase operations, making it easier to use in the application.
"""
from firebase_admin import firestore
from flask import current_app
import datetime
from app import firebase_db

# Check if Firebase is available
def is_firebase_available():
    """Check if Firebase is initialized and available for use"""
    return hasattr(firebase_db, 'db') and firebase_db.db is not None

# Helper functions
def to_dict(doc_snapshot):
    """Convert document snapshot to dict with id"""
    if not doc_snapshot.exists:
        return None
    data = doc_snapshot.to_dict()
    data['id'] = doc_snapshot.id
    return data

def format_datetime(dt):
    """Format datetime for display"""
    if hasattr(dt, 'todate'):
        return dt.todate().strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(dt, (str, datetime.datetime)):
        if isinstance(dt, str):
            try:
                dt = datetime.datetime.fromisoformat(dt)
            except ValueError:
                return dt
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt

# User operations
def get_users(limit=None, role=None):
    """Get all users, optionally filtered by role"""
    try:
        users_ref = firebase_db.users_ref()
        
        # Apply role filter if provided
        if role:
            query = users_ref.where('role', '==', role)
        else:
            query = users_ref
        
        # Apply limit if provided
        if limit:
            query = query.limit(limit)
        
        # Get users
        docs = query.get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting users: {e}")
        return []

def get_user(user_id):
    """Get a user by ID"""
    try:
        doc = firebase_db.users_ref().document(user_id).get()
        return to_dict(doc)
    except Exception as e:
        current_app.logger.error(f"Error getting user {user_id}: {e}")
        return None

def update_user(user_id, user_data):
    """Update a user"""
    try:
        user_data['updated_at'] = firestore.SERVER_TIMESTAMP
        firebase_db.users_ref().document(user_id).update(user_data)
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating user {user_id}: {e}")
        return False

def delete_user(user_id):
    """Delete a user and all related data"""
    try:
        # Start a batch operation
        batch = firebase_db.db.batch()
        
        # Delete user's complaints
        complaints = get_user_complaints(user_id)
        for complaint in complaints:
            # Delete complaint media
            delete_complaint_media_for_complaint(complaint['id'])
            
            # Delete complaint updates
            updates = get_complaint_updates(complaint['id'])
            for update in updates:
                batch.delete(firebase_db.complaint_updates_ref().document(update['id']))
            
            # Delete feedback
            feedback = get_complaint_feedback(complaint['id'])
            if feedback:
                batch.delete(firebase_db.feedbacks_ref().document(feedback['id']))
            
            # Delete complaint
            batch.delete(firebase_db.complaints_ref().document(complaint['id']))
        
        # Delete user's notifications
        notifications = get_user_notifications(user_id)
        for notification in notifications:
            batch.delete(firebase_db.notifications_ref().document(notification['id']))
        
        # Delete user's official requests
        official_requests = get_user_official_requests(user_id)
        for request in official_requests:
            batch.delete(firebase_db.official_requests_ref().document(request['id']))
        
        # Update official requests where user is reviewer
        reviewer_requests = firebase_db.official_requests_ref().where('reviewed_by', '==', user_id).get()
        for doc in reviewer_requests:
            batch.update(doc.reference, {'reviewed_by': None})
        
        # Delete the user document
        batch.delete(firebase_db.users_ref().document(user_id))
        
        # Commit the batch
        batch.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting user {user_id}: {e}")
        return False

# Category operations
def get_categories():
    """Get all categories"""
    try:
        docs = firebase_db.categories_ref().get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting categories: {e}")
        return []

def get_category(category_id):
    """Get a category by ID"""
    try:
        doc = firebase_db.categories_ref().document(category_id).get()
        return to_dict(doc)
    except Exception as e:
        current_app.logger.error(f"Error getting category {category_id}: {e}")
        return None

def create_category(category_data):
    """Create a new category"""
    try:
        doc_ref = firebase_db.categories_ref().document()
        doc_ref.set(category_data)
        category_data['id'] = doc_ref.id
        return category_data
    except Exception as e:
        current_app.logger.error(f"Error creating category: {e}")
        return None

def update_category(category_id, category_data):
    """Update a category"""
    try:
        firebase_db.categories_ref().document(category_id).update(category_data)
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating category {category_id}: {e}")
        return False

def delete_category(category_id):
    """Delete a category"""
    try:
        # Check if any complaints use this category
        complaints = firebase_db.complaints_ref().where('category_id', '==', category_id).limit(1).get()
        if len(list(complaints)) > 0:
            return False, "Cannot delete category with existing complaints"
        
        # Delete the category
        firebase_db.categories_ref().document(category_id).delete()
        return True, None
    except Exception as e:
        current_app.logger.error(f"Error deleting category {category_id}: {e}")
        return False, str(e)

# Complaint operations
def get_complaints(limit=None, offset=0, status=None, category_id=None, user_id=None, search_query=None):
    """Get complaints with optional filters"""
    try:
        query = firebase_db.complaints_ref().order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Apply filters
        if status:
            query = query.where('status', '==', status)
        
        if category_id:
            query = query.where('category_id', '==', category_id)
            
        if user_id:
            query = query.where('user_id', '==', user_id)
        
        # Note: Firestore doesn't support complex text search natively
        # For search_query, we would need to use a different approach like Algolia
        # For now, we'll get all results and filter in Python
        
        # Get results
        docs = query.get()
        results = []
        
        for doc in docs:
            item = to_dict(doc)
            
            # Filter by search query if provided
            if search_query:
                text_to_search = (item.get('title', '') + ' ' + 
                                  item.get('description', '') + ' ' + 
                                  item.get('location', '')).lower()
                
                if search_query.lower() not in text_to_search:
                    continue
            
            results.append(item)
        
        # Apply pagination manually
        if offset > 0:
            results = results[offset:]
        
        if limit:
            results = results[:limit]
            
        return results
    except Exception as e:
        current_app.logger.error(f"Error getting complaints: {e}")
        return []

def get_complaint(complaint_id):
    """Get a complaint by ID"""
    try:
        doc = firebase_db.complaints_ref().document(complaint_id).get()
        complaint = to_dict(doc)
        
        if complaint:
            # Get category information
            try:
                category = get_category(complaint['category_id'])
                complaint['category_name'] = category['name'] if category else 'Unknown'
            except Exception as e:
                current_app.logger.error(f"Error getting category for complaint {complaint_id}: {e}")
                complaint['category_name'] = 'Unknown'
            
            # Get user information
            try:
                user = get_user(complaint['user_id'])
                if user:
                    complaint['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                    complaint['user_email'] = user.get('email', 'Unknown')
                else:
                    complaint['user_name'] = 'Unknown User'
                    complaint['user_email'] = 'Unknown'
            except Exception as e:
                current_app.logger.error(f"Error getting user for complaint {complaint_id}: {e}")
                complaint['user_name'] = 'Unknown User'
                complaint['user_email'] = 'Unknown'
            
            # Get assigned user information
            if complaint.get('assigned_to_id'):
                try:
                    assigned_user = get_user(complaint['assigned_to_id'])
                    if assigned_user:
                        complaint['assigned_to_name'] = f"{assigned_user.get('first_name', '')} {assigned_user.get('last_name', '')}"
                    else:
                        complaint['assigned_to_name'] = 'Unknown User'
                except Exception as e:
                    current_app.logger.error(f"Error getting assigned user for complaint {complaint_id}: {e}")
                    complaint['assigned_to_name'] = 'Unknown User'
            
            # Get media attachments
            try:
                complaint['media_attachments'] = get_complaint_media(complaint_id)
            except Exception as e:
                current_app.logger.error(f"Error getting media for complaint {complaint_id}: {e}")
                complaint['media_attachments'] = []
        
        return complaint
    except Exception as e:
        current_app.logger.error(f"Error getting complaint {complaint_id}: {e}")
        return None

def create_complaint(complaint_data):
    """Create a new complaint"""
    try:
        complaint_data['created_at'] = firestore.SERVER_TIMESTAMP
        complaint_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        doc_ref = firebase_db.complaints_ref().document()
        doc_ref.set(complaint_data)
        
        complaint_data['id'] = doc_ref.id
        return complaint_data
    except Exception as e:
        current_app.logger.error(f"Error creating complaint: {e}")
        return None

def update_complaint(complaint_id, complaint_data):
    """Update a complaint"""
    try:
        complaint_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        # Handle special fields for status changes
        if 'status' in complaint_data:
            # Get current complaint
            current_complaint = get_complaint(complaint_id)
            
            # If resolving the complaint, set resolved_at
            if complaint_data['status'] == 'resolved' and (not current_complaint or current_complaint.get('status') != 'resolved'):
                complaint_data['resolved_at'] = firestore.SERVER_TIMESTAMP
            
            # If unresolving the complaint, clear resolved_at
            elif current_complaint and current_complaint.get('status') == 'resolved' and complaint_data['status'] != 'resolved':
                complaint_data['resolved_at'] = None
        
        # Update the complaint
        firebase_db.complaints_ref().document(complaint_id).update(complaint_data)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating complaint {complaint_id}: {e}")
        return False

def delete_complaint(complaint_id):
    """Delete a complaint and all related data"""
    try:
        # Start a batch operation
        batch = firebase_db.db.batch()
        
        # Delete complaint media
        delete_complaint_media_for_complaint(complaint_id)
        
        # Delete complaint updates
        updates_query = firebase_db.complaint_updates_ref().where('complaint_id', '==', complaint_id)
        updates = list(updates_query.stream())
        for update_doc in updates:
            batch.delete(update_doc.reference)
        
        # Delete feedback
        feedback_query = firebase_db.feedbacks_ref().where('complaint_id', '==', complaint_id)
        feedbacks = list(feedback_query.stream())
        for feedback_doc in feedbacks:
            batch.delete(feedback_doc.reference)
        
        # Delete notifications related to this complaint
        try:
            notifications_query = firebase_db.notifications_ref().where('complaint_id', '==', complaint_id)
            notifications = list(notifications_query.stream())
            for notification_doc in notifications:
                batch.delete(notification_doc.reference)
        except Exception as e:
            current_app.logger.error(f"Error deleting notifications for complaint {complaint_id}: {e}")
        
        # Delete the complaint document
        batch.delete(firebase_db.complaints_ref().document(complaint_id))
        
        # Commit the batch
        batch.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting complaint {complaint_id}: {e}")
        return False

def get_user_complaints(user_id, limit=None):
    """Get complaints for a specific user"""
    try:
        query = firebase_db.complaints_ref().where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting complaints for user {user_id}: {e}")
        return []

# Complaint media operations
def get_complaint_media(complaint_id):
    """Get all media for a complaint"""
    try:
        query = firebase_db.complaint_media_ref().where('complaint_id', '==', complaint_id)
        docs = query.get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting media for complaint {complaint_id}: {e}")
        return []

def create_complaint_media(media_data):
    """Create a new complaint media entry"""
    try:
        media_data['created_at'] = firestore.SERVER_TIMESTAMP
        doc_ref = firebase_db.complaint_media_ref().document()
        doc_ref.set(media_data)
        media_data['id'] = doc_ref.id
        return media_data
    except Exception as e:
        current_app.logger.error(f"Error creating complaint media: {e}")
        return None

def delete_complaint_media(media_id):
    """Delete a complaint media entry"""
    try:
        return firebase_db.delete_complaint_media(media_id)
    except Exception as e:
        current_app.logger.error(f"Error deleting complaint media {media_id}: {e}")
        return False

def delete_complaint_media_for_complaint(complaint_id):
    """Delete all media for a complaint"""
    try:
        return firebase_db.delete_complaint_media_for_complaint(complaint_id)
    except Exception as e:
        current_app.logger.error(f"Error deleting media for complaint {complaint_id}: {e}")
        return False

# Complaint update operations
def get_complaint_updates(complaint_id):
    """Get all updates for a complaint"""
    try:
        query = firebase_db.complaint_updates_ref().where('complaint_id', '==', complaint_id).order_by('created_at')
        docs = query.get()
        updates = []
        
        for doc in docs:
            update = to_dict(doc)
            
            # Get user information
            try:
                user = get_user(update['user_id'])
                if user:
                    update['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                else:
                    update['user_name'] = 'Unknown User'
            except Exception as e:
                current_app.logger.error(f"Error getting user for update {update['id']}: {e}")
                update['user_name'] = 'Unknown User'
            
            updates.append(update)
        
        return updates
    except Exception as e:
        current_app.logger.error(f"Error getting updates for complaint {complaint_id}: {e}")
        return []

def create_complaint_update(update_data):
    """Create a new complaint update"""
    try:
        update_data['created_at'] = firestore.SERVER_TIMESTAMP
        doc_ref = firebase_db.complaint_updates_ref().document()
        doc_ref.set(update_data)
        
        # Update the complaint status
        if 'complaint_id' in update_data and 'status' in update_data:
            firebase_db.complaints_ref().document(update_data['complaint_id']).update({
                'status': update_data['status'],
                'updated_at': firestore.SERVER_TIMESTAMP,
                'resolved_at': firestore.SERVER_TIMESTAMP if update_data['status'] == 'resolved' else None
            })
        
        update_data['id'] = doc_ref.id
        return update_data
    except Exception as e:
        current_app.logger.error(f"Error creating complaint update: {e}")
        return None

# Feedback operations
def get_complaint_feedback(complaint_id):
    """Get feedback for a complaint"""
    try:
        query = firebase_db.feedbacks_ref().where('complaint_id', '==', complaint_id).limit(1)
        docs = query.get()
        
        if docs:
            feedback = to_dict(docs[0])
            
            # Get user information
            try:
                user = get_user(feedback['user_id'])
                if user:
                    feedback['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                else:
                    feedback['user_name'] = 'Unknown User'
            except Exception as e:
                current_app.logger.error(f"Error getting user for feedback {feedback['id']}: {e}")
                feedback['user_name'] = 'Unknown User'
            
            return feedback
        
        return None
    except Exception as e:
        current_app.logger.error(f"Error getting feedback for complaint {complaint_id}: {e}")
        return None

def create_feedback(feedback_data):
    """Create a new feedback"""
    try:
        feedback_data['created_at'] = firestore.SERVER_TIMESTAMP
        doc_ref = firebase_db.feedbacks_ref().document()
        doc_ref.set(feedback_data)
        
        feedback_data['id'] = doc_ref.id
        return feedback_data
    except Exception as e:
        current_app.logger.error(f"Error creating feedback: {e}")
        return None

def get_all_feedback():
    """Get all feedback for reports"""
    try:
        docs = firebase_db.feedbacks_ref().get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting all feedback: {e}")
        return []

# Notification operations
def get_user_notifications(user_id, limit=None, unread_only=False):
    """Get notifications for a user"""
    try:
        query = firebase_db.notifications_ref().where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if unread_only:
            query = query.where('is_read', '==', False)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting notifications for user {user_id}: {e}")
        return []

def create_notification(notification_data):
    """Create a new notification"""
    try:
        notification_data['created_at'] = firestore.SERVER_TIMESTAMP
        notification_data['is_read'] = False
        
        doc_ref = firebase_db.notifications_ref().document()
        doc_ref.set(notification_data)
        
        notification_data['id'] = doc_ref.id
        return notification_data
    except Exception as e:
        current_app.logger.error(f"Error creating notification: {e}")
        return None

def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        firebase_db.notifications_ref().document(notification_id).update({
            'is_read': True
        })
        return True
    except Exception as e:
        current_app.logger.error(f"Error marking notification {notification_id} as read: {e}")
        return False

def mark_all_notifications_read(user_id):
    """Mark all notifications for a user as read"""
    try:
        # Get all unread notifications
        query = firebase_db.notifications_ref().where('user_id', '==', user_id).where('is_read', '==', False)
        docs = query.get()
        
        # Create a batch operation
        batch = firebase_db.db.batch()
        
        for doc in docs:
            batch.update(doc.reference, {'is_read': True})
        
        # Commit the batch
        batch.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read for user {user_id}: {e}")
        return False

# Official request operations
def get_official_requests(status=None):
    """Get official requests, optionally filtered by status"""
    try:
        query = firebase_db.official_requests_ref().order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if status:
            query = query.where('status', '==', status)
        
        docs = query.get()
        requests = []
        
        for doc in docs:
            request = to_dict(doc)
            
            # Get user information
            try:
                user = get_user(request['user_id'])
                if user:
                    request['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                    request['user_email'] = user.get('email', 'Unknown')
                else:
                    request['user_name'] = 'Unknown User'
                    request['user_email'] = 'Unknown'
            except Exception as e:
                current_app.logger.error(f"Error getting user for request {request['id']}: {e}")
                request['user_name'] = 'Unknown User'
                request['user_email'] = 'Unknown'
            
            # Get reviewer information
            if request.get('reviewed_by'):
                try:
                    reviewer = get_user(request['reviewed_by'])
                    if reviewer:
                        request['reviewer_name'] = f"{reviewer.get('first_name', '')} {reviewer.get('last_name', '')}"
                    else:
                        request['reviewer_name'] = 'Unknown User'
                except Exception as e:
                    current_app.logger.error(f"Error getting reviewer for request {request['id']}: {e}")
                    request['reviewer_name'] = 'Unknown User'
            
            requests.append(request)
        
        return requests
    except Exception as e:
        current_app.logger.error(f"Error getting official requests: {e}")
        return []

def get_user_official_requests(user_id):
    """Get official requests for a user"""
    try:
        query = firebase_db.official_requests_ref().where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        docs = query.get()
        return [to_dict(doc) for doc in docs]
    except Exception as e:
        current_app.logger.error(f"Error getting official requests for user {user_id}: {e}")
        return []

def create_official_request(request_data):
    """Create a new official request"""
    try:
        request_data['created_at'] = firestore.SERVER_TIMESTAMP
        request_data['status'] = 'pending'
        
        doc_ref = firebase_db.official_requests_ref().document()
        doc_ref.set(request_data)
        
        request_data['id'] = doc_ref.id
        return request_data
    except Exception as e:
        current_app.logger.error(f"Error creating official request: {e}")
        return None

def review_official_request(request_id, review_data):
    """Review an official request"""
    try:
        review_data['reviewed_at'] = firestore.SERVER_TIMESTAMP
        firebase_db.official_requests_ref().document(request_id).update(review_data)
        
        # If approved, update the user role
        if review_data.get('status') == 'approved':
            # Get the request
            request_doc = firebase_db.official_requests_ref().document(request_id).get()
            request = to_dict(request_doc)
            
            if request and request.get('user_id'):
                # Update the user role
                firebase_db.users_ref().document(request['user_id']).update({
                    'role': 'official',
                    'department': request.get('department'),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                # Create notification for user
                create_notification({
                    'user_id': request['user_id'],
                    'title': 'Official Account Approved',
                    'message': f'Your request for an official account has been approved. You now have official privileges for the {request.get("department")} department.'
                })
            
        elif review_data.get('status') == 'rejected':
            # Get the request
            request_doc = firebase_db.official_requests_ref().document(request_id).get()
            request = to_dict(request_doc)
            
            if request and request.get('user_id'):
                # Create notification for user
                create_notification({
                    'user_id': request['user_id'],
                    'title': 'Official Account Request Rejected',
                    'message': f'Your request for an official account has been rejected. Reason: {review_data.get("review_notes", "No reason provided.")}'
                })
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error reviewing official request {request_id}: {e}")
        return False

# Audit log operations
def create_audit_log(log_data):
    """Create a new audit log entry"""
    try:
        log_data['created_at'] = firestore.SERVER_TIMESTAMP
        return firebase_db.create_audit_log(log_data)
    except Exception as e:
        current_app.logger.error(f"Error creating audit log: {e}")
        return None

def get_audit_logs(limit=None, offset=0):
    """Get audit logs with optional pagination"""
    try:
        query = firebase_db.audit_logs_ref().order_by('created_at', direction=firestore.Query.DESCENDING)
        
        docs = query.get()
        logs = [to_dict(doc) for doc in docs]
        
        # Apply pagination manually
        if offset > 0:
            logs = logs[offset:]
        
        if limit:
            logs = logs[:limit]
            
        # Enhance logs with user information
        for log in logs:
            if log.get('user_id'):
                try:
                    user = get_user(log['user_id'])
                    if user:
                        log['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                    else:
                        log['user_name'] = 'Unknown User'
                except Exception as e:
                    current_app.logger.error(f"Error getting user for log {log['id']}: {e}")
                    log['user_name'] = 'Unknown User'
        
        return logs
    except Exception as e:
        current_app.logger.error(f"Error getting audit logs: {e}")
        return []

# Statistics and reports
def get_complaint_statistics():
    """Get statistics about complaints"""
    try:
        # Get all complaints
        complaints = firebase_db.complaints_ref().get()
        
        # Count by status
        status_counts = {
            'total': 0,
            'pending': 0,
            'in_progress': 0,
            'resolved': 0,
            'rejected': 0
        }
        
        # Calculate resolution times for resolved complaints
        resolution_times = []
        
        for doc in complaints:
            complaint = to_dict(doc)
            status = complaint.get('status', 'pending')
            
            status_counts['total'] += 1
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Calculate resolution time for resolved complaints
            if status == 'resolved' and complaint.get('created_at') and complaint.get('resolved_at'):
                try:
                    # Convert timestamps to datetime objects if needed
                    created_at = complaint['created_at']
                    resolved_at = complaint['resolved_at']
                    
                    if hasattr(created_at, 'todate'):
                        created_at = created_at.todate()
                    elif isinstance(created_at, str):
                        created_at = datetime.datetime.fromisoformat(created_at)
                    
                    if hasattr(resolved_at, 'todate'):
                        resolved_at = resolved_at.todate()
                    elif isinstance(resolved_at, str):
                        resolved_at = datetime.datetime.fromisoformat(resolved_at)
                    
                    # Calculate time difference in days
                    diff = (resolved_at - created_at).total_seconds() / 86400
                    resolution_times.append(diff)
                except Exception as e:
                    current_app.logger.error(f"Error calculating resolution time: {e}")
        
        # Calculate resolution statistics
        resolution_stats = {
            'avg_time': sum(resolution_times) / len(resolution_times) if resolution_times else None,
            'min_time': min(resolution_times) if resolution_times else None,
            'max_time': max(resolution_times) if resolution_times else None
        }
        
        # Get category statistics
        category_stats = []
        categories = get_categories()
        
        for category in categories:
            # Count complaints in this category
            category_complaints = firebase_db.complaints_ref().where('category_id', '==', category['id']).get()
            
            # Count by status
            total = 0
            resolved = 0
            pending = 0
            in_progress = 0
            rejected = 0
            
            for doc in category_complaints:
                complaint = to_dict(doc)
                status = complaint.get('status', 'pending')
                
                total += 1
                if status == 'resolved':
                    resolved += 1
                elif status == 'pending':
                    pending += 1
                elif status == 'in_progress':
                    in_progress += 1
                elif status == 'rejected':
                    rejected += 1
            
            category_stats.append({
                'name': category['name'],
                'total': total,
                'resolved': resolved,
                'pending': pending,
                'in_progress': in_progress,
                'rejected': rejected
            })
        
        # Get feedback statistics
        feedback = get_all_feedback()
        
        avg_rating = sum(f['rating'] for f in feedback) / len(feedback) if feedback else 0
        
        # Count ratings
        rating_counts = {}
        for f in feedback:
            rating = f['rating']
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        feedback_stats = [{'rating': k, 'count': v} for k, v in rating_counts.items()]
        
        # Get top locations
        location_counts = {}
        for doc in complaints:
            complaint = to_dict(doc)
            location = complaint.get('location', 'Unknown')
            location_counts[location] = location_counts.get(location, 0) + 1
        
        # Sort by count and get top 10
        top_locations = sorted(
            [{'location': k, 'count': v} for k, v in location_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        
        return {
            'status_counts': status_counts,
            'resolution_stats': resolution_stats,
            'category_stats': category_stats,
            'avg_rating': avg_rating,
            'feedback_stats': feedback_stats,
            'top_locations': top_locations
        }
    except Exception as e:
        current_app.logger.error(f"Error getting complaint statistics: {e}")
        return {
            'status_counts': {'total': 0, 'pending': 0, 'in_progress': 0, 'resolved': 0, 'rejected': 0},
            'resolution_stats': {'avg_time': None, 'min_time': None, 'max_time': None},
            'category_stats': [],
            'avg_rating': 0,
            'feedback_stats': [],
            'top_locations': []
        } 