from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, desc, case
from app import db
from app.models import User, Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification, OfficialRequest, ComplaintMedia
from app.forms import ComplaintUpdateForm, SearchForm
from app.utils.email import send_complaint_notification
from app.utils.notifications import send_notification_to_role, send_notification_to_department
from app.utils.decorators import admin_required, official_required
from functools import wraps

admin = Blueprint('admin', __name__)

# Decorator to restrict access to admins and officials
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Decorator to restrict access to admins and officials
def officials_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'official']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Check before each request to admin blueprint
@admin.before_request
def restrict_to_admins_and_officials():
    if not current_user.is_authenticated or current_user.role not in ['admin', 'official']:
        abort(403)

@admin.route('/')
@admin.route('/dashboard')
def dashboard():
    """Admin dashboard route"""
    # Get complaint stats from SQLite
    try:
        # Count complaints by status
        total_complaints = Complaint.query.count()
        pending_count = Complaint.query.filter_by(status='pending').count()
        in_progress_count = Complaint.query.filter_by(status='in_progress').count()
        resolved_count = Complaint.query.filter_by(status='resolved').count()
        rejected_count = Complaint.query.filter_by(status='rejected').count()
        
        # Get recent complaints with joined data
        recent_complaints = Complaint.query.order_by(desc(Complaint.created_at)).limit(5).all()
        
        # Get user stats
        total_users = User.query.count()
        citizen_count = User.query.filter_by(role='citizen').count()
        official_count = User.query.filter_by(role='official').count()
        admin_count = User.query.filter_by(role='admin').count()
        
        # Count pending official requests (for admin)
        official_requests_count = 0
        if current_user.role == 'admin':
            official_requests_count = OfficialRequest.query.filter_by(status='pending').count()
        
        # Get feedback stats
        avg_rating = db.session.query(func.avg(Feedback.rating)).scalar() or 0
        # Round to one decimal place
        avg_rating = round(avg_rating, 1)
        
        # Get department stats if user is an official
        if current_user.role == 'official' and current_user.department:
            # Get categories for this department
            department_categories = Category.query.filter_by(department=current_user.department).all()
            category_ids = [c.id for c in department_categories]
            
            # Only count complaints in this department
            if category_ids:
                dept_total = Complaint.query.filter(Complaint.category_id.in_(category_ids)).count()
                dept_pending = Complaint.query.filter(
                    Complaint.category_id.in_(category_ids),
                    Complaint.status == 'pending'
                ).count()
                dept_in_progress = Complaint.query.filter(
                    Complaint.category_id.in_(category_ids),
                    Complaint.status == 'in_progress'
                ).count()
                dept_resolved = Complaint.query.filter(
                    Complaint.category_id.in_(category_ids),
                    Complaint.status == 'resolved'
                ).count()
                
                # Assigned to current user
                assigned_to_me = Complaint.query.filter_by(
                    assigned_to_id=current_user.id
                ).count()
            else:
                dept_total = 0
                dept_pending = 0
                dept_in_progress = 0
                dept_resolved = 0
                assigned_to_me = 0
                
            department_stats = {
                'total': dept_total,
                'pending': dept_pending,
                'in_progress': dept_in_progress,
                'resolved': dept_resolved,
                'assigned_to_me': assigned_to_me
            }
        else:
            department_stats = None
        
        # Calculate resolution time (average days between creation and resolution)
        resolution_time_query = db.session.query(
            func.avg(func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at))
        ).filter(Complaint.status == 'resolved')
        
        avg_resolution_time = resolution_time_query.scalar() or 0
        
        # High priority complaints in pending or in_progress status
        high_priority_count = Complaint.query.filter(
            Complaint.priority.in_(['high', 'urgent']),
            Complaint.status.in_(['pending', 'in_progress'])
        ).count()
        
        # Prepare data for category distribution chart
        categories = Category.query.all()
        category_stats = []
        
        for category in categories:
            count = Complaint.query.filter_by(category_id=category.id).count()
            if count > 0:
                category_stats.append({
                    'name': category.name,
                    'count': count
                })
        
        # Sort by count descending
        category_stats.sort(key=lambda x: x['count'], reverse=True)
    
        return render_template('admin/dashboard.html',
                              total_complaints=total_complaints,
                              pending_count=pending_count,
                              in_progress_count=in_progress_count,
                              resolved_count=resolved_count,
                              rejected_count=rejected_count,
                              recent_complaints=recent_complaints,
                              total_users=total_users,
                              citizen_count=citizen_count,
                              official_count=official_count,
                              admin_count=admin_count,
                              avg_rating=avg_rating,
                              department_stats=department_stats,
                              avg_resolution_time=avg_resolution_time,
                              high_priority_count=high_priority_count,
                              category_stats=category_stats,
                              official_requests_count=official_requests_count)
                              
    except Exception as e:
        current_app.logger.error(f"Error generating dashboard: {e}")
        flash("There was an error loading the dashboard. Please try again later.", "danger")
        return render_template('admin/dashboard.html',
                              error=True)

@admin.route('/complaints')
@login_required
def complaints():
    """List and search all complaints"""
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    
    # Populate category choices for the form
    form.category.choices = [(0, 'All')] + [(c.id, c.name) for c in Category.query.order_by('name')]
    
    # Base query
    query = Complaint.query
    
    # Apply filters
    search_query = request.args.get('search_query', '')
    if search_query:
        query = query.filter(Complaint.title.contains(search_query) | 
                           Complaint.description.contains(search_query) |
                           Complaint.location.contains(search_query))
    
    category_id = request.args.get('category', 0, type=int)
    if category_id > 0:
        query = query.filter_by(category_id=category_id)
    
    status = request.args.get('status', '')
    if status in ['pending', 'in_progress', 'resolved', 'rejected']:
        query = query.filter_by(status=status)
    
    priority = request.args.get('priority', '')
    if priority in ['low', 'medium', 'high', 'urgent']:
        query = query.filter_by(priority=priority)
    
    # If official, only show complaints in their department
    if current_user.role == 'official' and current_user.department:
        # Find categories assigned to this department
        category_ids = [c.id for c in Category.query.filter_by(department=current_user.department).all()]
        query = query.filter(Complaint.category_id.in_(category_ids))
    
    # Sort by newest first
    query = query.order_by(Complaint.created_at.desc())
    
    # Paginate results
    complaints = query.paginate(
        page=page,
        per_page=current_app.config['COMPLAINTS_PER_PAGE'],
        error_out=False
    )
    
    return render_template('admin/complaints.html',
                          complaints=complaints,
                          form=form)

@admin.route('/complaint/<complaint_id>', methods=['GET', 'POST'])
@login_required
def complaint_detail(complaint_id):
    """View details of a specific complaint"""
    # Get complaint from SQLite
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Debug log for request method
    current_app.logger.debug(f"Request method: {request.method}")
    if request.method == 'POST':
        current_app.logger.debug(f"Form data: {request.form}")
            
    # Get user information
    user = User.query.get(complaint.user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.complaints'))
    
    # Get complaint updates
    updates = ComplaintUpdate.query.filter_by(complaint_id=complaint.id).order_by(ComplaintUpdate.created_at).all()
    
    # Get category information
    category = Category.query.get(complaint.category_id)
    
    form = ComplaintUpdateForm()
    
    # Set up the assigned_to field based on user role
    if current_user.role == 'admin':
        # For admins, show dropdown with all officials
        if category and category.department:
            officials = User.query.filter_by(role='official', department=category.department).all()
        else:
            officials = User.query.filter_by(role='official').all()
        
        # Add empty option and officials to choices
        form.assigned_to.choices = [(0, 'Unassigned')] + [(u.id, f"{u.full_name()} ({u.department})") for u in officials]
    else:
        # For officials, just set their own ID without showing dropdown
        form.assigned_to.choices = [(current_user.id, f"{current_user.full_name()} ({current_user.department})")]
    
    # Debug log for form validation
    if request.method == 'POST':
        current_app.logger.debug(f"Form validation errors: {form.errors}")
        current_app.logger.debug(f"Form data before validation: status={form.status.data}, priority={form.priority.data}, comment={form.comment.data}")
    
    if form.validate_on_submit():
        current_app.logger.debug("Form validation successful")
        try:
            # Update complaint
            old_status = complaint.status
            old_priority = complaint.priority
            complaint.status = form.status.data
            complaint.priority = form.priority.data
            if form.assigned_to.data:
                complaint.assigned_to_id = form.assigned_to.data
            complaint.updated_at = datetime.utcnow()
            
            current_app.logger.debug(f"Updating complaint status from {old_status} to {complaint.status}")
            
            # Create status update
            update = ComplaintUpdate(
                complaint_id=complaint.id,
                user_id=current_user.id,
                status=form.status.data,
                comment=form.comment.data,
                created_at=datetime.utcnow()
            )
            db.session.add(update)
            
            # Auto-assign to the current official when updating status
            # This ensures the complaint is always assigned to the person who last updated it
            if current_user.role == 'official' and complaint.assigned_to_id != current_user.id:
                was_previously_assigned = complaint.assigned_to_id is not None
                complaint.assigned_to_id = current_user.id
                complaint.assigned_at = datetime.utcnow()
                
                # Add assignment info to the update comment if empty
                if not form.comment.data:
                    update.comment = f"Assigned to {current_user.full_name()} ({current_user.department})"
                
                # Create audit log for assignment
                assignment_log = AuditLog(
                    user_id=current_user.id,
                    action='assign_complaint',
                    resource_type='complaint',
                    resource_id=complaint.id,
                    details=f'Complaint assigned to {current_user.username} ({current_user.department})',
                    ip_address=request.remote_addr
                )
                db.session.add(assignment_log)
                
                # If this is the first assignment, notify the citizen
                if not was_previously_assigned:
                    assignment_notification = Notification(
                        user_id=complaint.user_id,
                        title="Complaint Assigned",
                        message=f"Your complaint '{complaint.title}' has been assigned to {current_user.full_name()} from the {current_user.department} department.",
                        created_at=datetime.utcnow()
                    )
                    notifications_to_send.append(assignment_notification)
            
            # For admins using the dropdown
            elif current_user.role == 'admin' and form.assigned_to.data != 0 and complaint.assigned_to_id != form.assigned_to.data:
                # Admin selected a specific official
                assigned_official = User.query.get(form.assigned_to.data)
                if assigned_official:
                    was_previously_assigned = complaint.assigned_to_id is not None
                    complaint.assigned_to_id = assigned_official.id
                    complaint.assigned_at = datetime.utcnow()
                    
                    # Add assignment info to the update comment if empty
                    if not form.comment.data:
                        update.comment = f"Assigned to {assigned_official.full_name()} ({assigned_official.department})"
                    
                    # Create audit log for assignment by admin
                    assignment_log = AuditLog(
                        user_id=current_user.id,
                        action='assign_complaint',
                        resource_type='complaint',
                        resource_id=complaint.id,
                        details=f'Complaint assigned to {assigned_official.username} ({assigned_official.department}) by admin',
                        ip_address=request.remote_addr
                    )
                    db.session.add(assignment_log)
                    
                    # If this is the first assignment, notify the citizen
                    if not was_previously_assigned:
                        assignment_notification = Notification(
                            user_id=complaint.user_id,
                            title="Complaint Assigned",
                            message=f"Your complaint '{complaint.title}' has been assigned to {assigned_official.full_name()} from the {assigned_official.department} department.",
                            created_at=datetime.utcnow()
                        )
                        notifications_to_send.append(assignment_notification)
            
            # Notifications for status and priority changes
            notifications_to_send = []
            
            # If status changed to resolved, set resolved date
            if form.status.data == 'resolved' and old_status != 'resolved':
                complaint.resolved_at = datetime.utcnow()
                
                # Create notification for citizen
                notification = Notification(
                    user_id=complaint.user_id,
                    title="Complaint Resolved",
                    message=f"Your complaint '{complaint.title}' has been marked as resolved. Please provide feedback.",
                    created_at=datetime.utcnow()
                )
                notifications_to_send.append(notification)
            # Send notification for all other status changes as well
            elif form.status.data != old_status:
                status_display = form.status.data.replace('_', ' ').title()
                
                # Create notification for citizen based on new status
                notification_messages = {
                    'pending': f"Your complaint '{complaint.title}' is now pending review.",
                    'in_progress': f"Your complaint '{complaint.title}' is now being processed by our team.",
                    'rejected': f"Your complaint '{complaint.title}' has been reviewed and cannot be processed. See comments for details."
                }
                
                message = notification_messages.get(form.status.data, f"Your complaint '{complaint.title}' status has been updated to {status_display}.")
                if form.comment.data:
                    message += f" Comment: {form.comment.data}"
                
                notification = Notification(
                    user_id=complaint.user_id,
                    title=f"Complaint Status: {status_display}",
                    message=message,
                    created_at=datetime.utcnow()
                )
                notifications_to_send.append(notification)
            
            # Send notification for priority changes
            if form.priority.data != old_priority:
                priority_display = form.priority.data.title()
                
                # Only send a priority notification if we haven't already sent a status change notification
                if form.status.data == old_status:
                    notification = Notification(
                        user_id=complaint.user_id,
                        title=f"Complaint Priority Updated",
                        message=f"Your complaint '{complaint.title}' priority has been updated to {priority_display}.",
                        created_at=datetime.utcnow()
                    )
                    notifications_to_send.append(notification)
            
            # Add all notifications to session and send emails
            citizen = User.query.get(complaint.user_id)
            for notification in notifications_to_send:
                db.session.add(notification)
                
                # Send email notification if user has an email
                if citizen and citizen.email and citizen.is_active:
                    try:
                        from app.utils.email import send_email
                        
                        # Format for email
                        email_text = f"""
                        Dear {citizen.full_name()},
                        
                        {notification.message}
                        
                        You can view the full complaint details and updates at:
                        {url_for('citizen.complaint_detail', complaint_id=complaint.id, _external=True)}
                        
                        Thank you for using CitySeva.
                        
                        Regards,
                        CitySeva Team
                        """
                        
                        # Send the email asynchronously 
                        send_email(
                            subject=notification.title,
                            recipients=[citizen.email],
                            text_body=email_text,
                            html_body=email_text.replace('\n', '<br>')
                        )
                        current_app.logger.info(f"Sent email notification to {citizen.email} about complaint {complaint.id}")
                    except Exception as e:
                        current_app.logger.error(f"Failed to send email notification: {e}")
                        # Don't stop the process if email fails
            
            # Create audit log
            audit_details = []
            if form.status.data != old_status:
                audit_details.append(f"status from '{old_status}' to '{form.status.data}'")
            if form.priority.data != old_priority:
                audit_details.append(f"priority from '{old_priority}' to '{form.priority.data}'")
            
            audit_detail_text = ", ".join(audit_details)
            if not audit_detail_text:
                audit_detail_text = "complaint details (no status/priority change)"
                
            audit = AuditLog(
                user_id=current_user.id,
                action='update_complaint',
                resource_type='complaint',
                resource_id=complaint.id,
                details=f'Updated {audit_detail_text}',
                ip_address=request.remote_addr
            )
            db.session.add(audit)
            
            db.session.commit()
            current_app.logger.debug("Database changes committed successfully")
            
            flash('Complaint updated successfully.', 'success')
            return redirect(url_for('admin.complaint_detail', complaint_id=complaint.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating complaint: {e}")
            flash('Error updating complaint. Please try again.', 'danger')
    else:
        current_app.logger.debug("Form validation failed")
    
    # Pre-populate form with current values
    form.status.data = complaint.status
    form.priority.data = complaint.priority
    form.assigned_to.data = complaint.assigned_to_id
    form.complaint_id.data = complaint.id
    
    # Check if feedback exists
    feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
    
    return render_template('admin/complaint_detail.html',
                          complaint=complaint,
                          user=user,
                          updates=updates,
                          category=category,
                          form=form,
                          feedback=feedback)

@admin.route('/categories')
@login_required
@admin_required
def categories():
    """Manage complaint categories"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@admin.route('/category/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Add a new category"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        department = request.form.get('department')
        icon = request.form.get('icon', 'fa-exclamation-circle')
        
        # Handle custom department if "Other" is selected
        if department == 'Other':
            other_department = request.form.get('other_department')
            if other_department and other_department.strip():
                department = other_department.strip()
            else:
                flash('Please specify the custom department name.', 'danger')
                return redirect(url_for('admin.add_category'))
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin.add_category'))
        
        # Check if category already exists
        exists = Category.query.filter_by(name=name).first()
        if exists:
            flash('A category with this name already exists.', 'danger')
            return redirect(url_for('admin.add_category'))
        
        category = Category(
            name=name,
            description=description,
            department=department,
            icon=icon
        )
        db.session.add(category)
        
        # Log creation
        log = AuditLog(
            user_id=current_user.id,
            action='create',
            resource_type='category',
            resource_id=None,  # Will be updated after commit
            details=f'Created category: {name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Update log with actual category ID
        log.resource_id = category.id
        db.session.commit()
        
        flash(f'Category {name} has been added.', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/add_category.html')

@admin.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit an existing category"""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        department = request.form.get('department')
        icon = request.form.get('icon')
        
        # Handle custom department if "Other" is selected
        if department == 'Other':
            other_department = request.form.get('other_department')
            if other_department and other_department.strip():
                department = other_department.strip()
            else:
                flash('Please specify the custom department name.', 'danger')
                return redirect(url_for('admin.edit_category', category_id=category.id))
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin.edit_category', category_id=category.id))
        
        # Check if new name conflicts with existing category
        exists = Category.query.filter(Category.name == name, Category.id != category_id).first()
        if exists:
            flash('A category with this name already exists.', 'danger')
            return redirect(url_for('admin.edit_category', category_id=category.id))
        
        category.name = name
        category.description = description
        category.department = department
        if icon:
            category.icon = icon
        
        # Log update
        log = AuditLog(
            user_id=current_user.id,
            action='update',
            resource_type='category',
            resource_id=category.id,
            details=f'Updated category: {name}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Category {name} has been updated.', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/edit_category.html', category=category)

@admin.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get users from SQLite
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
        
    return render_template('admin/users.html', users=users)

@admin.route('/user/<string:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle a user's active status"""
        # Use SQLite for data manipulation
    user = User.query.get_or_404(user_id)
        
        # Don't allow deactivating yourself
    if user.id == current_user.id:
            flash('You cannot deactivate your own account.', 'danger')
            return redirect(url_for('admin.users'))
        
    user.is_active = not user.is_active
        
        # Log action
    log = AuditLog(
            user_id=current_user.id,
            action='toggle_active',
            resource_type='user',
            resource_id=user.id,
            details=f'Set user active status to {user.is_active}',
            ip_address=request.remote_addr
        )
    db.session.add(log)
    db.session.commit()
        
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/user/<string:user_id>/make_official', methods=['POST'])
@login_required
@admin_required
def make_official(user_id):
    """Promote a user to official role"""
    department = request.form.get('department')
    
    if not department:
        flash('Department is required for officials.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Handle custom department if "Other" is selected
    if department == 'Other':
        other_department = request.form.get('other_department')
        if other_department and other_department.strip():
            department = other_department.strip()
        else:
            flash('Please specify the custom department name.', 'danger')
            return redirect(url_for('admin.users'))
    
        # Use SQLite for data manipulation
        user = User.query.get_or_404(user_id)
        
        # Update user
        user.role = 'official'
        user.department = department
        
        # Log action
        log = AuditLog(
            user_id=current_user.id,
            action='role_change',
            resource_type='user',
            resource_id=user.id,
            details=f'Changed user role to official in {department} department',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'User {user.username} has been promoted to official.', 'success')
        return redirect(url_for('admin.users'))

@admin.route('/user/<string:user_id>/make_admin', methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    """Promote a user to admin role"""
        # Use SQLite for data manipulation
    user = User.query.get_or_404(user_id)
        
    # Update user
    user.role = 'admin'
        
    # Log action
    log = AuditLog(
            user_id=current_user.id,
            action='role_change',
            resource_type='user',
            resource_id=user.id,
            details='Changed user role to admin',
            ip_address=request.remote_addr
        )
    db.session.add(log)
    db.session.commit()
        
    flash(f'User {user.username} has been promoted to admin.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/user/<string:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user from the system"""
    # Use SQLite for data manipulation
    user = User.query.get_or_404(user_id)
        
    # Don't allow deleting yourself
    if user.id == current_user.id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('admin.users'))
            
    # Check for confirmation
    if not request.form.get('confirm'):
            flash('Please confirm the deletion.', 'warning')
            return redirect(url_for('admin.users'))
        
    username = user.username  # Store for the flash message
        
    # Log action before deletion
    log = AuditLog(
            user_id=current_user.id,
            action='delete_user',
            resource_type='user',
            resource_id=user.id,
            details=f'Deleted user: {user.username} ({user.email})',
            ip_address=request.remote_addr
        )
    db.session.add(log)
        
    try:
            # Handle dependencies before deleting user
            
            # 1. Official Requests - delete where user is the requester
            OfficialRequest.query.filter_by(user_id=user.id).delete()
            
            # 2. Official Requests - set reviewer to NULL where user is the reviewer
            reviewer_requests = OfficialRequest.query.filter_by(reviewed_by=user.id).all()
            for req in reviewer_requests:
                req.reviewed_by = None
                req.reviewer = None
            
            # 3. Notifications - delete all notifications for this user
            Notification.query.filter_by(user_id=user.id).delete()
            
            # 4. Feedback - delete all feedback submitted by this user
            Feedback.query.filter_by(user_id=user.id).delete()
            
            # 5. Complaint Updates - delete all updates made by this user
            ComplaintUpdate.query.filter_by(user_id=user.id).delete()
            
            # 6. Complaints - handle complaints where user is assigned
            assigned_complaints = Complaint.query.filter_by(assigned_to_id=user.id).all()
            for complaint in assigned_complaints:
                complaint.assigned_to_id = None
                complaint.assigned_at = None
                
            # 7. Complaints - delete complaints submitted by this user
            # (This will also delete related updates and feedback due to cascade)
            Complaint.query.filter_by(user_id=user.id).delete()
            
            # 8. Audit Logs - set user_id to NULL for logs related to this user
            audit_logs = AuditLog.query.filter_by(user_id=user.id).all()
            for log in audit_logs:
                log.user_id = None
            
            # Finally, delete the user
            db.session.delete(user)
            db.session.commit()
            
            flash(f'User {username} has been permanently deleted.', 'success')
    except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'danger')
            
    return redirect(url_for('admin.users'))

@admin.route('/reports')
@login_required
def reports():
    """Generate reports and statistics"""
    # Date range filter
    # For simplicity, we'll show overall stats
    
    # Resolution time statistics (avg, min, max)
    # Get resolved complaints and calculate statistics in Python instead of at SQL level
    resolved_complaints = Complaint.query.filter_by(status='resolved').all()
    
    avg_time = None
    min_time = None
    max_time = None
    
    if resolved_complaints:
        # Calculate time differences in days
        time_diffs = []
        for complaint in resolved_complaints:
            if complaint.resolved_at and complaint.created_at:
                time_diff = (complaint.resolved_at - complaint.created_at).total_seconds() / 86400  # Convert to days
                time_diffs.append(time_diff)
        
        if time_diffs:
            avg_time = sum(time_diffs) / len(time_diffs)
            min_time = min(time_diffs)
            max_time = max(time_diffs)
    
    resolution_stats = {
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time
    }
    
    # Category statistics
    category_stats = db.session.query(
        Category.name,
        func.count(Complaint.id).label('total'),
        func.sum(case((Complaint.status == 'resolved', 1), else_=0)).label('resolved'),
        func.sum(case((Complaint.status == 'pending', 1), else_=0)).label('pending'),
        func.sum(case((Complaint.status == 'in_progress', 1), else_=0)).label('in_progress'),
        func.sum(case((Complaint.status == 'rejected', 1), else_=0)).label('rejected')
    ).join(Category).group_by(Category.name).all()
    
    # Feedback statistics
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar() or 0
    
    feedback_stats = db.session.query(
        Feedback.rating,
        func.count(Feedback.id).label('count')
    ).group_by(Feedback.rating).all()
    
    # Top locations with most complaints
    top_locations = db.session.query(
        Complaint.location,
        func.count(Complaint.id).label('count')
    ).group_by(Complaint.location).order_by(desc('count')).limit(10).all()
    
    return render_template('admin/reports.html',
                          resolution_stats=resolution_stats,
                          category_stats=category_stats,
                          avg_rating=avg_rating,
                          feedback_stats=feedback_stats,
                          top_locations=top_locations)

@admin.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """View system audit logs"""
    page = request.args.get('page', 1, type=int)
    
    logs = AuditLog.query.order_by(AuditLog.created_at.desc())\
                      .paginate(
                          page=page,
                          per_page=50,
                          error_out=False
                      )
    
    return render_template('admin/audit_logs.html', logs=logs)

@admin.route('/official-requests')
@login_required
@admin_required
def official_requests():
    """View and manage official account requests"""
    # Get pending requests
    pending_requests = OfficialRequest.query.filter_by(status='pending')\
                                         .order_by(OfficialRequest.created_at.desc()).all()
    
    # Get processed requests (limited to last 20)
    processed_requests = OfficialRequest.query.filter(OfficialRequest.status.in_(['approved', 'rejected']))\
                                          .order_by(OfficialRequest.reviewed_at.desc()).limit(20).all()
    
    return render_template('admin/official_requests.html',
                          pending_requests=pending_requests,
                          processed_requests=processed_requests)

@admin.route('/official-request/<int:request_id>/review', methods=['POST'])
@login_required
@admin_required
def review_official_request(request_id):
    """Review an official account request"""
    # Get the request
    official_request = OfficialRequest.query.get_or_404(request_id)
    
    # Check if it's already processed
    if official_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('admin.official_requests'))
    
    # Get form data
    decision = request.form.get('decision')
    review_notes = request.form.get('review_notes')
    
    if decision not in ['approved', 'rejected']:
        flash('Invalid decision.', 'danger')
        return redirect(url_for('admin.official_requests'))
    
    # Update the request
    official_request.status = decision
    official_request.reviewed_by = current_user.id
    official_request.reviewed_at = datetime.utcnow()
    official_request.review_notes = review_notes
    
    # If approved, update the user's role
    if decision == 'approved':
        user = User.query.get(official_request.user_id)
        if user:
            user.role = 'official'
            user.department = official_request.department
            
            # Notify the user
            notification = Notification(
                user_id=user.id,
                title='Official Account Approved',
                message=f'Your request for an official account has been approved. You can now log in as a government official for the {official_request.department} department.'
            )
            db.session.add(notification)
            
            # Create a more detailed notification with instructions
            detailed_notification = Notification(
                user_id=user.id,
                title='Welcome to Government Official Portal',
                message=f'As a verified government official for the {official_request.department} department, you now have access to department-specific features. Please log in using your credentials and select "{official_request.department}" from the department dropdown to access your administrative dashboard.'
            )
            db.session.add(detailed_notification)
    else:
        # If rejected, notify the user
        notification = Notification(
            user_id=official_request.user_id,
            title='Official Account Request Rejected',
            message=f'Your request for an official account has been rejected. Reason: {review_notes or "No reason provided."}'
        )
        db.session.add(notification)
    
    # Log the action
    log = AuditLog(
        user_id=current_user.id,
        action=f'official_request_{decision}',
        resource_type='official_request',
        resource_id=official_request.id,
        details=f'Official account request {decision}. Department: {official_request.department}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Official account request has been {decision}.', 'success')
    return redirect(url_for('admin.official_requests'))

@admin.route('/notifications')
@login_required
def admin_notifications():
    """View all notifications for the admin/official users"""
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
    notification_route = 'admin.admin_notifications'
    
    return render_template('shared/notifications.html', 
                          notifications=notifications,
                          notification_route=notification_route)

@admin.route('/complaint/<int:complaint_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_complaint(complaint_id):
    """Delete a complaint and all associated data"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check for confirmation
    if not request.form.get('confirm'):
        flash('Please confirm the deletion.', 'warning')
        return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))
    
    # Store data for flash message
    complaint_title = complaint.title
    complaint_id_str = str(complaint.id)
    
    try:
        # Also delete from SQLite for consistency
        try:
            # Delete all complaint updates
            ComplaintUpdate.query.filter_by(complaint_id=complaint.id).delete()
            
            # Delete feedback (if any)
            Feedback.query.filter_by(complaint_id=complaint.id).delete()
            
            # Delete media attachments
            ComplaintMedia.query.filter_by(complaint_id=complaint.id).delete()
            
            # Delete notifications related to this complaint
            try:
                # Try first approach - using complaint_id field if it exists
                Notification.query.filter_by(complaint_id=complaint.id).delete()
            except Exception as e:
                # If that fails, try using resource_id and resource_type
                try:
                    Notification.query.filter_by(resource_type='complaint', resource_id=complaint.id).delete()
                except Exception as e:
                    current_app.logger.warning(f"Could not delete notifications: {e}")
            
            # Create audit log entry
            log = AuditLog(
                user_id=current_user.id,
                action='delete_complaint',
                resource_type='complaint',
                resource_id=complaint.id,
                details=f'Deleted complaint: {complaint_title}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            
            # Finally, delete the complaint
            db.session.delete(complaint)
            db.session.commit()
            
            flash(f'Complaint "{complaint_title}" has been deleted.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting complaint: {e}")
            flash(f'Error deleting complaint: {e}', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting complaint: {e}")
        flash(f'Error deleting complaint: {e}', 'danger')
    
    return redirect(url_for('admin.complaints'))

@admin.route('/send-notification', methods=['GET', 'POST'])
@admin.route('/send_notification', methods=['GET', 'POST'])
@login_required
@admin_required
def send_notification():
    """Send notifications to users"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        message = request.form.get('message')
        recipients = request.form.get('recipients')
        department = request.form.get('department')
        
        if not title or not message or not recipients:
            flash('Title, message, and recipients are required.', 'danger')
            return redirect(url_for('admin.send_notification'))
        
        # Send to appropriate recipients
        sent_count = 0
        if recipients == 'all_users':
            # Send to all users
            admin_count = send_notification_to_role('admin', title, message)
            official_count = send_notification_to_role('official', title, message)
            citizen_count = send_notification_to_role('citizen', title, message)
            sent_count = admin_count + official_count + citizen_count
            recipient_text = 'all users'
        elif recipients == 'all_citizens':
            sent_count = send_notification_to_role('citizen', title, message)
            recipient_text = 'all citizens'
        elif recipients == 'all_officials':
            sent_count = send_notification_to_role('official', title, message)
            recipient_text = 'all officials'
        elif recipients == 'all_admins':
            sent_count = send_notification_to_role('admin', title, message)
            recipient_text = 'all administrators'
        elif recipients == 'department' and department:
            sent_count = send_notification_to_department(department, title, message)
            recipient_text = f'officials in {department} department'
        else:
            flash('Invalid recipient selection.', 'danger')
            return redirect(url_for('admin.send_notification'))
        
        # Create audit log
        log = AuditLog(
            user_id=current_user.id,
            action='send_notification',
            resource_type='notification',
            resource_id=None,
            details=f'Sent notification "{title}" to {recipient_text}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Notification sent to {sent_count} recipients.', 'success')
        return redirect(url_for('admin.dashboard'))
    
    # GET request - show form
    # Get all departments for the department dropdown
    departments = db.session.query(Category.department).distinct().all()
    department_list = [dept[0] for dept in departments if dept[0]]
    
    return render_template('admin/send_notification.html', 
                          departments=department_list)

@admin.route('/official-requests/<int:request_id>')
@login_required
@admin_required
def view_request(request_id):
    request = OfficialRequest.query.get_or_404(request_id)
    return render_template('admin/request_detail.html', request=request)

@admin.route('/official-request/<int:request_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_request(request_id):
    """Delete an official account request"""
    request = OfficialRequest.query.get_or_404(request_id)
    
    # Check if it's already processed
    if request.status != 'pending':
        flash('Cannot delete a processed request.', 'warning')
        return redirect(url_for('admin.official_requests'))
    
    # Log the action before deletion
    log = AuditLog(
        user_id=current_user.id,
        action='delete_official_request',
        resource_type='official_request',
        resource_id=request.id,
        details=f'Deleted official request from {request.user.full_name()} for {request.department} department',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    # Delete the request
    db.session.delete(request)
    db.session.commit()
    
    flash('Official account request has been deleted.', 'success')
    return redirect(url_for('admin.official_requests')) 