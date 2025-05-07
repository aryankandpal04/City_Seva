from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import current_app, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from app import db
from app.models import Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification
from app.forms import ComplaintForm, FeedbackForm, ProfileUpdateForm
from app.utils.email import send_complaint_notification

citizen = Blueprint('citizen', __name__)

@citizen.route('/')
def index():
    """Landing page for the application"""
    # If user is authenticated, redirect to dashboard
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'official']:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))
    
    # Basic stats for display on landing page
    total_complaints = Complaint.query.count()
    resolved_complaints = Complaint.query.filter_by(status='resolved').count()
    categories = Category.query.all()
    
    return render_template('citizen/index.html', 
                          total_complaints=total_complaints,
                          resolved_complaints=resolved_complaints,
                          categories=categories)

@citizen.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for citizen users"""
    if current_user.role in ['admin', 'official']:
        return redirect(url_for('admin.dashboard'))
    
    # Get recent complaints by this user
    recent_complaints = Complaint.query.filter_by(user_id=current_user.id)\
                                .order_by(Complaint.created_at.desc())\
                                .limit(5).all()
    
    # Get complaint status counts
    pending_count = Complaint.query.filter_by(user_id=current_user.id, status='pending').count()
    in_progress_count = Complaint.query.filter_by(user_id=current_user.id, status='in_progress').count()
    resolved_count = Complaint.query.filter_by(user_id=current_user.id, status='resolved').count()
    rejected_count = Complaint.query.filter_by(user_id=current_user.id, status='rejected').count()
    
    # Get unread notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                              .order_by(Notification.created_at.desc())\
                              .limit(5).all()
    
    return render_template('citizen/dashboard.html',
                          recent_complaints=recent_complaints,
                          pending_count=pending_count,
                          in_progress_count=in_progress_count,
                          resolved_count=resolved_count,
                          rejected_count=rejected_count,
                          notifications=notifications)

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
    
    # Check if categories exist, if not create them
    categories_count = Category.query.count()
    if categories_count == 0:
        # Create default categories if none exist
        default_categories = [
            {'name': 'Roads', 'description': 'Issues related to roads, potholes, and traffic signals', 'department': 'Public Works', 'icon': 'fa-road'},
            {'name': 'Water Supply', 'description': 'Issues related to water supply, leakages, and quality', 'department': 'Water Department', 'icon': 'fa-tint'},
            {'name': 'Electricity', 'description': 'Issues related to power outages, streetlights, and electrical hazards', 'department': 'Electricity Board', 'icon': 'fa-bolt'},
            {'name': 'Garbage', 'description': 'Issues related to waste collection, dumps, and cleanups', 'department': 'Sanitation', 'icon': 'fa-trash'},
            {'name': 'Parks & Playgrounds', 'description': 'Issues related to parks, playgrounds, and public spaces', 'department': 'Parks & Recreation', 'icon': 'fa-tree'},
            {'name': 'Public Transport', 'description': 'Issues related to buses, bus stops, and public transport', 'department': 'Transport', 'icon': 'fa-bus'},
            {'name': 'Stray Animals', 'description': 'Issues related to stray animals and animal control', 'department': 'Animal Control', 'icon': 'fa-paw'},
            {'name': 'Others', 'description': 'Other civic issues not covered in other categories', 'department': 'General Administration', 'icon': 'fa-exclamation-circle'}
        ]
        
        for cat_data in default_categories:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description'],
                department=cat_data['department'],
                icon=cat_data['icon']
            )
            db.session.add(category)
        
        db.session.commit()
        flash('Default categories have been created.', 'info')
    
    # Populate category choices
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name')]
    
    if form.validate_on_submit():
        # Handle image upload
        image_path = None
        if form.image.data:
            # Generate unique filename
            filename = secure_filename(f"{uuid.uuid4()}_{form.image.data.filename}")
            # Save file
            image_path = os.path.join('uploads', filename)
            form.image.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        # Create complaint
        complaint = Complaint(
            title=form.title.data,
            description=form.description.data,
            category_id=form.category_id.data,
            location=form.location.data,
            latitude=form.latitude.data or None,
            longitude=form.longitude.data or None,
            priority=form.priority.data,
            user_id=current_user.id,
            image_path=image_path
        )
        
        db.session.add(complaint)
        db.session.commit()
        
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
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.created_at.desc())\
                               .paginate(
                                   page=page,
                                   per_page=10,
                                   error_out=False
                               )
    
    # Mark notifications as read
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in unread:
        notification.is_read = True
    
    db.session.commit()
    
    return render_template('citizen/notifications.html', notifications=notifications)

@citizen.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename) 