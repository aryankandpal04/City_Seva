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
from sqlalchemy import desc
import mimetypes
from app.utils.notifications import send_complaint_notification_in_app

citizen = Blueprint('citizen', __name__)

@citizen.route('/')
def index():
    """Index route for citizens"""
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
    
    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    
    if form.validate_on_submit():
        try:
            # Create complaint in SQLite
            complaint = Complaint(
                title=form.title.data,
                description=form.description.data,
                category_id=form.category_id.data,
                location=form.location.data,
                latitude=float(form.latitude.data),
                longitude=float(form.longitude.data),
                priority=form.priority.data,
                user_id=current_user.id,
                status='pending',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(complaint)
            db.session.flush()  # Get the ID without committing
            
            # Create initial status update
            update = ComplaintUpdate(
                complaint_id=complaint.id,
                user_id=current_user.id,
                status='pending',
                comment='Complaint submitted',
                created_at=datetime.utcnow()
            )
            db.session.add(update)
            
            # Handle file upload if provided
            if form.media_files.data and form.media_files.data[0]:
                for media_file in form.media_files.data:
                    if media_file:
                        filename = secure_filename(media_file.filename)
                        # Generate unique filename
                        _, file_extension = os.path.splitext(filename)
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        
                        # Ensure upload directory exists
                        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        # Save file
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        media_file.save(file_path)
                                        
                        # Determine media type
                        mime_type = mimetypes.guess_type(file_path)[0]
                        media_type = 'image' if mime_type and mime_type.startswith('image') else 'video'
                        
                        # Create media record
                        media = ComplaintMedia(
                            complaint_id=complaint.id,
                            file_path=unique_filename,
                            media_type=media_type,
                            created_at=datetime.utcnow()
                        )
                        db.session.add(media)
                
            # Create audit log
            log = AuditLog(
                user_id=current_user.id,
                action='create_complaint',
                resource_type='complaint',
                resource_id=complaint.id,
                details=f'Created complaint: {complaint.title}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            
            # Commit all changes
            db.session.commit()
                
            # Send notification to officials
            category = Category.query.get(form.category_id.data)
            if category:
                # Send email notification
                email_success = False
                try:
                    email_success = send_complaint_notification(complaint, category)
                except Exception as e:
                    current_app.logger.error(f"Error sending email notification: {e}")
                
                # Send in-app notification
                app_notification_count = 0
                try:
                    app_notification_count = send_complaint_notification_in_app(complaint)
                except Exception as e:
                    current_app.logger.error(f"Error sending in-app notification: {e}")
                
                # Determine notification message based on results
                if email_success and app_notification_count > 0:
                    flash('Your complaint has been submitted and officials have been notified.', 'success')
                elif app_notification_count > 0:
                    flash('Your complaint has been submitted and officials have been notified in-app.', 'success')
                else:
                    flash('Your complaint has been submitted, but there was an error notifying officials.', 'warning')
            else:
                flash('Your complaint has been submitted.', 'success')
            
            return redirect(url_for('citizen.complaint_detail', complaint_id=complaint.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating complaint: {e}")
            flash(f'An error occurred while submitting your complaint: {str(e)}', 'danger')
    
    return render_template('citizen/new_complaint.html', form=form)

@citizen.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    """View details of a specific complaint"""
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
    # For SQLite, serve the file from local storage
    clean_filename = filename.replace('\\', '/')
    if '/' in clean_filename:
            clean_filename = clean_filename.split('/')[-1]
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], clean_filename) 