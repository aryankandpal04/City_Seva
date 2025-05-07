from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask import current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, desc, case
from app import db
from app.models import User, Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification
from app.forms import ComplaintUpdateForm, SearchForm
from app.utils.email import send_complaint_notification
from app.utils.decorators import admin_required, official_required

admin = Blueprint('admin', __name__)

@admin.before_request
def restrict_to_admins_and_officials():
    """Ensure only admins and officials can access admin routes"""
    if not current_user.is_authenticated or current_user.role not in ['admin', 'official']:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('citizen.index'))

@admin.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard showing overview of complaints"""
    # Summary statistics
    total_complaints = Complaint.query.count()
    pending_count = Complaint.query.filter_by(status='pending').count()
    in_progress_count = Complaint.query.filter_by(status='in_progress').count()
    resolved_count = Complaint.query.filter_by(status='resolved').count()
    rejected_count = Complaint.query.filter_by(status='rejected').count()
    
    # Recent complaints
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(10).all()
    
    # If official, only show complaints in their department
    if current_user.role == 'official' and current_user.department:
        # Find categories assigned to this department
        category_ids = [c.id for c in Category.query.filter_by(department=current_user.department).all()]
        
        # Filter complaints by those categories
        total_complaints = Complaint.query.filter(Complaint.category_id.in_(category_ids)).count()
        pending_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                             Complaint.status == 'pending').count()
        in_progress_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                                 Complaint.status == 'in_progress').count()
        resolved_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                              Complaint.status == 'resolved').count()
        rejected_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                              Complaint.status == 'rejected').count()
        
        recent_complaints = Complaint.query.filter(Complaint.category_id.in_(category_ids))\
                                         .order_by(Complaint.created_at.desc()).limit(10).all()
    
    # Complaints assigned to current official
    if current_user.role == 'official':
        assigned_complaints = Complaint.query.filter_by(assigned_to_id=current_user.id)\
                                          .order_by(Complaint.created_at.desc()).limit(5).all()
    else:
        assigned_complaints = []
    
    # Category distribution for pie chart
    category_stats = db.session.query(
        Category.name, func.count(Complaint.id)
    ).join(Complaint).group_by(Category.name).all()
    
    # Priority distribution for pie chart
    priority_stats = db.session.query(
        Complaint.priority, func.count(Complaint.id)
    ).group_by(Complaint.priority).all()
    
    # Timeline data for last 30 days
    # (Note: This would be more efficient with a database-specific date function)
    # For simplicity, we'll show monthly data here
    
    return render_template('admin/dashboard.html',
                          total_complaints=total_complaints,
                          pending_count=pending_count,
                          in_progress_count=in_progress_count,
                          resolved_count=resolved_count,
                          rejected_count=rejected_count,
                          recent_complaints=recent_complaints,
                          assigned_complaints=assigned_complaints,
                          category_stats=category_stats,
                          priority_stats=priority_stats)

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

@admin.route('/complaint/<int:complaint_id>', methods=['GET', 'POST'])
@login_required
def complaint_detail(complaint_id):
    """View and update a specific complaint"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # If official, check if they have access to this complaint's category
    if current_user.role == 'official' and current_user.department:
        category = Category.query.get(complaint.category_id)
        if category.department != current_user.department:
            flash('You do not have permission to view this complaint.', 'danger')
            return redirect(url_for('admin.complaints'))
    
    # Get all updates for this complaint
    updates = ComplaintUpdate.query.filter_by(complaint_id=complaint.id)\
                              .order_by(ComplaintUpdate.created_at).all()
    
    # Form for updating complaint
    form = ComplaintUpdateForm()
    
    # Populate assigned_to choices with officials
    form.assigned_to_id.choices = [(0, 'Unassigned')] + [
        (u.id, f"{u.full_name()} ({u.department})") 
        for u in User.query.filter_by(role='official').order_by(User.first_name).all()
    ]
    
    if form.validate_on_submit():
        # Check if status changed
        status_changed = complaint.status != form.status.data
        old_status = complaint.status
        
        # Update complaint
        complaint.status = form.status.data
        
        # Update assigned_to if changed
        if form.assigned_to_id.data != 0:  # Not "Unassigned"
            complaint.assigned_to_id = form.assigned_to_id.data
            complaint.assigned_at = datetime.utcnow()
        elif complaint.assigned_to_id is not None:  # Was assigned before
            complaint.assigned_to_id = None
            complaint.assigned_at = None
        
        # Handle status-specific actions
        if status_changed:
            if form.status.data == 'resolved':
                complaint.resolved_at = datetime.utcnow()
            elif old_status == 'resolved':
                # If moving from resolved to another status, clear resolved_at
                complaint.resolved_at = None
        
        # Create update record
        update = ComplaintUpdate(
            complaint_id=complaint.id,
            user_id=current_user.id,
            status=form.status.data,
            comment=form.comment.data
        )
        db.session.add(update)
        
        # Add audit log entry
        log = AuditLog(
            user_id=current_user.id,
            action='update',
            resource_type='complaint',
            resource_id=complaint.id,
            details=f'Updated complaint status to {form.status.data}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        # Create notification for the complaint owner
        notification = Notification(
            user_id=complaint.user_id,
            title=f'Complaint #{complaint.id} Updated',
            message=f'Your complaint "{complaint.title}" has been updated to {form.status.data}.'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Send email notification
        try:
            send_complaint_notification(
                complaint.author,
                complaint, 
                status_change=f'from {old_status} to {form.status.data}'
            )
        except Exception as e:
            # Just log the error but don't prevent the update
            print(f"Error sending email: {e}")
        
        flash('Complaint has been updated.', 'success')
        return redirect(url_for('admin.complaint_detail', complaint_id=complaint.id))
    
    # Pre-populate form with current values
    if request.method == 'GET':
        form.status.data = complaint.status
        form.assigned_to_id.data = complaint.assigned_to_id or 0
    
    return render_template('admin/complaint_detail.html',
                          complaint=complaint,
                          updates=updates,
                          form=form)

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
    """Manage users"""
    role_filter = request.args.get('role', '')
    
    query = User.query
    
    if role_filter in ['citizen', 'official', 'admin']:
        query = query.filter_by(role=role_filter)
    
    users = query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/users.html', users=users)

@admin.route('/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle a user's active status"""
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

@admin.route('/user/<int:user_id>/make_official', methods=['POST'])
@login_required
@admin_required
def make_official(user_id):
    """Promote a user to official role"""
    user = User.query.get_or_404(user_id)
    department = request.form.get('department')
    
    if not department:
        flash('Department is required for officials.', 'danger')
        return redirect(url_for('admin.users'))
    
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

@admin.route('/user/<int:user_id>/make_admin', methods=['POST'])
@login_required
@admin_required
def make_admin(user_id):
    """Promote a user to admin role"""
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

@admin.route('/reports')
@login_required
def reports():
    """Generate reports and statistics"""
    # Date range filter
    # For simplicity, we'll show overall stats
    
    # Resolution time statistics (avg, min, max)
    resolution_stats = db.session.query(
        func.avg(Complaint.resolved_at - Complaint.created_at).label('avg_time'),
        func.min(Complaint.resolved_at - Complaint.created_at).label('min_time'),
        func.max(Complaint.resolved_at - Complaint.created_at).label('max_time')
    ).filter(Complaint.status == 'resolved').first()
    
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