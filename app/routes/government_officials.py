from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc, func
from app import db
from app.models import User, Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification, ComplaintMedia
from app.forms.admin import ComplaintUpdateForm, SearchForm
from app.utils.decorators import official_required
from functools import wraps

government_officials = Blueprint('government_officials', __name__)

# Check before each request to government_officials blueprint
@government_officials.before_request
def restrict_to_officials():
    if not current_user.is_authenticated or current_user.role != 'official':
        abort(403)

@government_officials.route('/dashboard')
@login_required
def dashboard():
    """Official dashboard route"""
    # Get complaint stats from SQLite for this official's department
    try:
        # Count complaints by status in this department
        department = current_user.department
        
        # Get categories for this department
        department_categories = Category.query.filter_by(department=department).all()
        category_ids = [c.id for c in department_categories]
        
        # Only count complaints in this department
        if category_ids:
            total_complaints = Complaint.query.filter(Complaint.category_id.in_(category_ids)).count()
            pending_count = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'pending'
            ).count()
            in_progress_count = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'in_progress'
            ).count()
            resolved_count = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'resolved'
            ).count()
            rejected_count = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'rejected'
            ).count()
            
            # Assigned to current user
            assigned_to_me = Complaint.query.filter_by(
                assigned_to_id=current_user.id
            ).count()
            
            # High priority complaints in this department
            high_priority_count = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.priority.in_(['high', 'urgent']),
                Complaint.status.in_(['pending', 'in_progress'])
            ).count()
            
            # Get recent assigned complaints
            assigned_complaints = Complaint.query.filter_by(
                assigned_to_id=current_user.id
            ).order_by(desc(Complaint.created_at)).limit(5).all()
            
            # Get recent department complaints
            dept_complaints = Complaint.query.filter(
                Complaint.category_id.in_(category_ids)
            ).order_by(desc(Complaint.created_at)).limit(10).all()
            
        else:
            # No categories for this department
            total_complaints = 0
            pending_count = 0
            in_progress_count = 0
            resolved_count = 0
            rejected_count = 0
            assigned_to_me = 0
            high_priority_count = 0
            assigned_complaints = []
            dept_complaints = []
        
        # Get feedback stats for this official
        avg_rating = db.session.query(
            func.avg(Feedback.rating)
        ).join(Complaint).filter(
            Complaint.assigned_to_id == current_user.id,
            Complaint.status == 'resolved'
        ).scalar() or 0
        
        # Round to one decimal place
        avg_rating = round(avg_rating, 1)
        
        return render_template('government_officials/dashboard.html',
                              total_complaints=total_complaints,
                              pending_count=pending_count,
                              in_progress_count=in_progress_count,
                              resolved_count=resolved_count,
                              rejected_count=rejected_count,
                              high_priority_count=high_priority_count,
                              assigned_to_me=assigned_to_me,
                              assigned_complaints=assigned_complaints,
                              dept_complaints=dept_complaints,
                              avg_rating=avg_rating)
    
    except Exception as e:
        current_app.logger.error(f"Error generating dashboard: {e}")
        flash("There was an error loading the dashboard. Please try again later.", "danger")
        return render_template('government_officials/dashboard.html',
                              error=True)

@government_officials.route('/assigned')
@login_required
def assigned_complaints():
    """List and search complaints assigned to this official"""
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    
    # Populate category choices for the form
    department = current_user.department
    categories = Category.query.filter_by(department=department).order_by('name').all()
    form.category.choices = [(0, 'All')] + [(c.id, c.name) for c in categories]
    
    # Base query - only complaints assigned to this official
    query = Complaint.query.filter_by(assigned_to_id=current_user.id)
    
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
    
    # Sort by newest first
    query = query.order_by(Complaint.created_at.desc())
    
    # Paginate results
    complaints = query.paginate(
        page=page,
        per_page=current_app.config['COMPLAINTS_PER_PAGE'],
        error_out=False
    )
    
    return render_template('government_officials/assigned_complaints.html',
                          complaints=complaints,
                          form=form)

@government_officials.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Government official profile page"""
    # Placeholder for profile page
    return render_template('government_officials/profile.html')

@government_officials.route('/reports')
@login_required
def reports():
    """Reports and analytics for officials"""
    # Placeholder for reports page
    return render_template('government_officials/reports.html')

@government_officials.route('/complaint/<complaint_id>')
@login_required
def complaint_detail(complaint_id):
    """View details of a specific complaint - redirects to admin route"""
    # Redirects to the admin route which handles both admin and official views
    return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))

@government_officials.route('/export-report/<report_type>')
@login_required
def export_report(report_type):
    """Export reports to CSV or PDF"""
    # Placeholder for export functionality
    flash(f"Export {report_type} report functionality not yet implemented", "info")
    return redirect(url_for('government_officials.reports')) 