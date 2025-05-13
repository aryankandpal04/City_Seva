from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask import current_app, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from app import db
from app.models import Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification, ComplaintMedia
from app.forms import ComplaintForm, FeedbackForm, ProfileUpdateForm
from app.utils.email import send_complaint_notification
from app import firebase_db
from sqlalchemy import desc
import mimetypes
from google.cloud import firestore
from app.routes.admin import FirestorePagination

citizen = Blueprint('citizen', __name__)

@citizen.route('/')
def index():
    """Index route for citizens"""
    # Check if Firebase is enabled
    if hasattr(firebase_db, 'db') and firebase_db.db is not None:
        # Use Firebase for data retrieval
        total_complaints = len(firebase_db.get_all_complaints())
        resolved_complaints = len(firebase_db.complaints_ref().where('status', '==', 'resolved').get())
        pending_complaints = len(firebase_db.complaints_ref().where('status', '==', 'pending').get())
        in_progress_complaints = len(firebase_db.complaints_ref().where('status', '==', 'in_progress').get())
        
        # Get categories
        categories = firebase_db.get_all_categories()
    else:
        # Use SQLite for data retrieval
        total_complaints = Complaint.query.count()
        resolved_complaints = Complaint.query.filter_by(status='resolved').count()
        pending_complaints = Complaint.query.filter_by(status='pending').count()
        in_progress_complaints = Complaint.query.filter_by(status='in_progress').count()
        
        # Get categories
        categories = Category.query.all()
    
    return render_template('citizen/index.html',
                          total_complaints=total_complaints,
                          resolved_complaints=resolved_complaints,
                          pending_complaints=pending_complaints,
                          in_progress_complaints=in_progress_complaints,
                          categories=categories)

@citizen.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for citizens"""
    # Check if Firebase is enabled
    if hasattr(firebase_db, 'db') and firebase_db.db is not None:
        # Use Firebase for data retrieval
        user_id = str(current_user.id)
        recent_complaints = firebase_db.get_user_complaints(user_id, limit=5)
        
        # Get statuses count
        total_complaints = len(firebase_db.complaints_ref().where('user_id', '==', user_id).get())
        pending_count = len(firebase_db.complaints_ref().where('user_id', '==', user_id).where('status', '==', 'pending').get())
        in_progress_count = len(firebase_db.complaints_ref().where('user_id', '==', user_id).where('status', '==', 'in_progress').get())
        resolved_count = len(firebase_db.complaints_ref().where('user_id', '==', user_id).where('status', '==', 'resolved').get())
        rejected_count = len(firebase_db.complaints_ref().where('user_id', '==', user_id).where('status', '==', 'rejected').get())
        
        # Get unread notifications count
        unread_notifications = 0
        if hasattr(firebase_db, 'db'):
            try:
                notifications_ref = firebase_db.db.collection('notifications')
                unread_count = len(notifications_ref.where('user_id', '==', user_id).where('is_read', '==', False).get())
                unread_notifications = unread_count
            except Exception as e:
                current_app.logger.error(f"Error getting notifications: {e}")
    else:
        # Use SQLite for data retrieval
        recent_complaints = Complaint.query.filter_by(user_id=current_user.id) \
            .order_by(desc(Complaint.created_at)) \
            .limit(5).all()
            
        total_complaints = Complaint.query.filter_by(user_id=current_user.id).count()
        pending_count = Complaint.query.filter_by(user_id=current_user.id, status='pending').count()
        in_progress_count = Complaint.query.filter_by(user_id=current_user.id, status='in_progress').count()
        resolved_count = Complaint.query.filter_by(user_id=current_user.id, status='resolved').count()
        rejected_count = Complaint.query.filter_by(user_id=current_user.id, status='rejected').count()
        
        # Get unread notifications count
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('citizen/dashboard.html',
                          recent_complaints=recent_complaints,
                          total_complaints=total_complaints,
                          pending_count=pending_count,
                          in_progress_count=in_progress_count,
                          resolved_count=resolved_count,
                          rejected_count=rejected_count,
                          unread_notifications=unread_notifications)

@citizen.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    form = ProfileUpdateForm()
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        
        db.session.commit()
        
        # Log profile update
        log = AuditLog(
            user_id=current_user.id,
            action='profile_update',
            resource_type='user',
            resource_id=current_user.id,
            details='User updated profile',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('citizen.profile'))
    
    # Pre-populate form with current user data
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
        form.address.data = current_user.address
    
    return render_template('citizen/profile.html', form=form)

@citizen.route('/complaints')
@login_required
def complaints():
    """List all complaints submitted by the user"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)
    
    # Check if Firebase is enabled
    use_firebase = hasattr(firebase_db, 'db') and firebase_db.db is not None
    
    if use_firebase:
        # Use Firebase for data retrieval
        user_id = str(current_user.id)
        
        # Base query - get complaints for current user
        query = firebase_db.complaints_ref().where('user_id', '==', user_id)
        
        # Apply status filter if provided
        if status_filter and status_filter in ['pending', 'in_progress', 'resolved', 'rejected']:
            query = query.where('status', '==', status_filter)
        
        # Order by created_at descending
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Get all results (pagination handled in template)
        all_complaints = list(query.stream())
        total_complaints = len(all_complaints)
        
        # Manual pagination
        per_page = current_app.config['COMPLAINTS_PER_PAGE']
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Get the subset for this page
        complaints_for_page = all_complaints[start_idx:end_idx]
        
        # Convert to dict format
        complaints_data = [firebase_db.to_dict(doc) for doc in complaints_for_page]
        
        # Create a custom pagination class to mimic SQLAlchemy's pagination
        complaints = FirestorePagination(complaints_data, page, per_page, total_complaints)
        
        return render_template('citizen/complaints.html', complaints=complaints)
    else:
        # Use SQLite for data retrieval
        # Base query - get complaints for current user
        query = Complaint.query.filter_by(user_id=current_user.id)
        
        # Apply status filter if provided
        if status_filter and status_filter in ['pending', 'in_progress', 'resolved', 'rejected']:
            query = query.filter_by(status=status_filter)
        
        # Get paginated results
        complaints = query.order_by(Complaint.created_at.desc())\
                        .paginate(
                            page=page, 
                            per_page=current_app.config['COMPLAINTS_PER_PAGE'],
                            error_out=False
                        )
        
        return render_template('citizen/complaints.html', complaints=complaints)

@citizen.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    """Create a new complaint"""
    form = ComplaintForm()
    
    # Check if categories exist, if not create default categories
    categories_count = Category.query.count()
    if categories_count == 0:
        # Create default categories
        categories = [
            Category(name='Roads and Infrastructure', department='Public Works'),
            Category(name='Water Supply', department='Water Department'),
            Category(name='Electricity', department='Electricity Department'),
            Category(name='Garbage Collection', department='Sanitation'),
            Category(name='Public Transport', department='Transport'),
            Category(name='Parks and Recreation', department='Parks Department'),
            Category(name='Street Lighting', department='Electricity Department'),
            Category(name='Drainage', department='Public Works'),
            Category(name='Public Safety', department='Police'),
            Category(name='Others', department='General')
        ]
        db.session.bulk_save_objects(categories)
        db.session.commit()
        flash('Default categories have been created.', 'info')
    
    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    
    if form.validate_on_submit():
        # Check if Firebase is enabled
        use_firebase = hasattr(firebase_db, 'db') and firebase_db.db is not None
        
        # Create complaint
        if use_firebase:
            # Create complaint in Firebase
            user_id = str(current_user.id)
            category_id = str(form.category_id.data)
            
            complaint_data = {
                'title': form.title.data,
                'description': form.description.data,
                'category_id': category_id,
                'location': form.location.data,
                'latitude': float(form.latitude.data),
                'longitude': float(form.longitude.data),
                'priority': form.priority.data,
                'user_id': user_id,
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Save complaint in Firestore
            firebase_complaint = firebase_db.create_complaint(complaint_data)
            complaint_id = firebase_complaint['id']
            
            # Handle multiple media uploads
            media_files = []
            if form.media_files.data:
                for file in form.media_files.data:
                    if file.filename:  # Check if a file was actually selected
                        # Get file extension
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        
                        # Determine media type
                        media_type = None
                        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                            media_type = 'image'
                        elif file_ext in ['.mp4', '.mov', '.avi']:
                            media_type = 'video'
                        
                        if media_type:
                            # Generate unique filename
                            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                            storage_path = f"complaints/{complaint_id}/media/{filename}"
                            
                            # Get file position and reset it before upload
                            file.seek(0)
                            
                            # Upload to Firebase Storage
                            file_url = firebase_db.upload_file(file, storage_path)
                            
                            if file_url:
                                # Create media entry in Firestore
                                media_data = {
                                    'complaint_id': complaint_id,
                                    'file_url': file_url,
                                    'storage_path': storage_path,
                                    'media_type': media_type,
                                    'filename': filename
                                }
                                
                                media_record = firebase_db.create_complaint_media(media_data)
                                media_files.append(media_record)
            
            # Create initial update
            update_data = {
                'complaint_id': complaint_id,
                'user_id': user_id,
                'status': 'pending',
                'comment': 'Complaint submitted',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            firebase_db.complaint_updates_ref().add(update_data)
            
            # Log complaint creation
            firebase_db.create_audit_log({
                'user_id': user_id,
                'action': 'create',
                'resource_type': 'complaint',
                'resource_id': complaint_id,
                'details': f'Created complaint: {form.title.data}',
                'ip_address': request.remote_addr,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            flash('Your complaint has been submitted.', 'success')
            return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))
        else:
            # Create complaint in SQLite
            complaint = Complaint(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category_id.data,
                location=form.location.data,
                latitude=form.latitude.data,
                longitude=form.longitude.data,
                priority=form.priority.data,
                user_id=current_user.id
            )
            
            db.session.add(complaint)
            db.session.flush()  # Get the complaint ID without committing yet
            
            # Handle multiple media uploads
            media_files = []
            if form.media_files.data:
                for file in form.media_files.data:
                    if file.filename:  # Check if a file was actually selected
                        # Get file extension
                        file_ext = os.path.splitext(file.filename)[1].lower()
                        
                        # Determine media type
                        media_type = None
                        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                            media_type = 'image'
                        elif file_ext in ['.mp4', '.mov', '.avi']:
                            media_type = 'video'
                        
                        if media_type:
                            # Generate unique filename
                            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                            # Save file
                            file_path = f"uploads/{filename}"  # Use forward slash for consistent paths in DB
                            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                            # Ensure upload directory exists
                            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                            file.save(upload_path)
                            
                            # Create media attachment record
                            media = ComplaintMedia(
                                complaint_id=complaint.id,
                                file_path=file_path,
                                media_type=media_type
                            )
                            media_files.append(media)
            
            # Add all media files
            if media_files:
                db.session.add_all(media_files)
                
                # For backward compatibility, set the first media as the primary one
                if media_files:
                    complaint.media_path = media_files[0].file_path
                    complaint.media_type = media_files[0].media_type
            
            # Create initial update
            update = ComplaintUpdate(
                complaint_id=complaint.id,
                user_id=current_user.id,
                status='pending',
                comment='Complaint submitted'
            )
            
            db.session.add(update)
            
            # Log complaint creation
            log = AuditLog(
                user_id=current_user.id,
                action='create',
                resource_type='complaint',
                resource_id=complaint.id,
                details=f'Created complaint: {complaint.title}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Your complaint has been submitted.', 'success')
            return redirect(url_for('citizen.complaint_detail', complaint_id=complaint.id))
    
    return render_template('citizen/new_complaint.html', form=form)

@citizen.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    """View details of a specific complaint"""
    # Check if Firebase is enabled
    use_firebase = hasattr(firebase_db, 'db') and firebase_db.db is not None
    
    if use_firebase:
        # Get complaint from Firebase
        firebase_complaint = firebase_db.get_complaint(str(complaint_id))
        if not firebase_complaint:
            abort(404)
        
        # Check if current user is authorized to view this complaint
        if firebase_complaint['user_id'] != str(current_user.id) and current_user.role not in ['admin', 'official']:
            flash('You are not authorized to view this complaint.', 'danger')
            return redirect(url_for('citizen.complaints'))
        
        # Get all updates for this complaint
        updates = firebase_db.complaint_updates_ref().where('complaint_id', '==', str(complaint_id)).order_by('created_at').get()
        updates = [firebase_db.to_dict(update) for update in updates]
        
        # Get all media attachments for this complaint
        media_attachments = firebase_db.get_complaint_media(str(complaint_id))
        
        # Check if feedback can be provided (only for resolved complaints)
        feedbacks = firebase_db.feedbacks_ref().where('complaint_id', '==', str(complaint_id)).limit(1).get()
        feedback = firebase_db.to_dict(feedbacks[0]) if feedbacks else None
        can_provide_feedback = firebase_complaint.get('status') == 'resolved' and not feedback
        
        # Add media_attachments to the complaint
        firebase_complaint['media_attachments'] = media_attachments
        
        return render_template('citizen/complaint_detail.html', 
                              complaint=firebase_complaint,
                              updates=updates,
                              can_provide_feedback=can_provide_feedback)
    else:
        # Use SQLite for data retrieval
        complaint = Complaint.query.get_or_404(complaint_id)
        
        # Check if current user is authorized to view this complaint
        if complaint.user_id != current_user.id and current_user.role not in ['admin', 'official']:
            flash('You are not authorized to view this complaint.', 'danger')
            return redirect(url_for('citizen.complaints'))
        
        # Get all updates for this complaint
        updates = ComplaintUpdate.query.filter_by(complaint_id=complaint.id)\
                                .order_by(ComplaintUpdate.created_at).all()
        
        # Check if feedback can be provided (only for resolved complaints)
        can_provide_feedback = complaint.status == 'resolved' and not complaint.feedback
        
        return render_template('citizen/complaint_detail.html', 
                              complaint=complaint,
                              updates=updates,
                              can_provide_feedback=can_provide_feedback)

@citizen.route('/complaint/<int:complaint_id>/feedback', methods=['GET', 'POST'])
@login_required
def provide_feedback(complaint_id):
    """Provide feedback for a resolved complaint"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if current user is authorized and complaint is resolved
    if complaint.user_id != current_user.id:
        flash('You are not authorized to provide feedback for this complaint.', 'danger')
        return redirect(url_for('citizen.complaints'))
    
    if complaint.status != 'resolved':
        flash('Feedback can only be provided for resolved complaints.', 'warning')
        return redirect(url_for('citizen.complaint_detail', complaint_id=complaint.id))
    
    # Check if feedback already exists
    if complaint.feedback:
        flash('You have already provided feedback for this complaint.', 'info')
        return redirect(url_for('citizen.complaint_detail', complaint_id=complaint.id))
    
    form = FeedbackForm()
    
    if form.validate_on_submit():
        feedback = Feedback(
            complaint_id=complaint.id,
            user_id=current_user.id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        
        db.session.add(feedback)
        
        # Log feedback submission
        log = AuditLog(
            user_id=current_user.id,
            action='feedback',
            resource_type='complaint',
            resource_id=complaint.id,
            details=f'Provided feedback with rating: {form.rating.data}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('citizen.complaint_detail', complaint_id=complaint.id))
    
    return render_template('citizen/provide_feedback.html', 
                          complaint=complaint,
                          form=form)

@citizen.route('/notifications')
@login_required
def notifications():
    """View all notifications for the current user"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Check if Firebase is enabled
    use_firebase = current_app.config.get('USE_FIREBASE', False)
    
    if use_firebase:
        try:
            # Create a FirestorePagination instance for notifications
            # Get all notifications for this user
            query = firebase_db.notifications_ref().where('user_id', '==', current_user.uid)
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            # Count total notifications for pagination
            all_docs = list(query.stream())
            total = len(all_docs)
            
            # Calculate offset and limit for current page
            offset = (page - 1) * per_page
            limit = per_page
            
            # Get the limited set of notifications for this page
            if offset < total:
                page_docs = all_docs[offset:offset+limit]
                notifications_data = [firebase_db.to_dict(doc) for doc in page_docs]
            else:
                notifications_data = []
            
            # Create pagination object
            notifications = FirestorePagination(notifications_data, page, per_page, total)
            
            # Mark notifications as read
            batch = firebase_db.db.batch()
            
            # Query only unread notifications
            unread_query = firebase_db.notifications_ref().where('user_id', '==', current_user.uid).where('is_read', '==', False)
            unread_docs = unread_query.stream()
            
            for doc in unread_docs:
                doc_ref = firebase_db.notifications_ref().document(doc.id)
                batch.update(doc_ref, {'is_read': True})
            
            # Commit the batch
            batch.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error getting Firebase notifications: {e}")
            flash("There was an error retrieving your notifications. Please try again later.", "danger")
            return redirect(url_for('citizen.dashboard'))
    else:
        # Use SQLite for notifications
        notifications = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.created_at.desc())\
                               .paginate(
                                   page=page,
                                   per_page=per_page,
                                   error_out=False
                               )
        
        # Mark notifications as read
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
        for notification in unread:
            notification.is_read = True
        
        db.session.commit()
    
    # Set the notification route for pagination links
    notification_route = 'citizen.notifications'
    
    return render_template('shared/notifications.html',
                          notifications=notifications,
                          notification_route=notification_route)

@citizen.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    # Check if Firebase is enabled
    use_firebase = hasattr(firebase_db, 'db') and firebase_db.db is not None
    
    if use_firebase:
        # For Firebase, redirect to the Firebase Storage URL
        # This function is called only for legacy files not yet migrated to Firebase
        clean_filename = filename.replace('\\', '/')
        if '/' in clean_filename:
            clean_filename = clean_filename.split('/')[-1]
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], clean_filename)
    else:
        # For SQLite, serve the file from local storage
        clean_filename = filename.replace('\\', '/')
        if '/' in clean_filename:
            clean_filename = clean_filename.split('/')[-1]
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], clean_filename) 