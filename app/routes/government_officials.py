from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import desc, func, case, extract
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

            # Get high priority complaints for display
            priority_complaints = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.priority.in_(['high', 'urgent']),
                Complaint.status.in_(['pending', 'in_progress'])
            ).order_by(desc(Complaint.created_at)).limit(5).all()
            
            # Get trend data for the last 12 months
            end_date = datetime.utcnow().replace(day=1)  # First day of current month
            start_date = end_date - timedelta(days=365)  # Approximately 12 months ago
            
            trend_data = db.session.query(
                extract('year', Complaint.created_at).label('year'),
                extract('month', Complaint.created_at).label('month'),
                func.count(Complaint.id).label('count')
            ).filter(
                Complaint.category_id.in_(category_ids),
                Complaint.created_at >= start_date,
                Complaint.created_at < end_date
            ).group_by('year', 'month').order_by('year', 'month').all()
            
            trend_dates = []
            trend_counts = []
            
            # Process the trend data
            current_date = start_date
            while current_date < end_date:
                month_name = current_date.strftime('%b %Y')
                trend_dates.append(month_name)
                
                # Find count for this month
                count = 0
                for data in trend_data:
                    if data.year == current_date.year and data.month == current_date.month:
                        count = data.count
                        break
                
                trend_counts.append(count)
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            # Get resolution trend data
            resolution_trend = db.session.query(
                extract('year', Complaint.resolved_at).label('year'),
                extract('month', Complaint.resolved_at).label('month'),
                func.count(Complaint.id).label('count')
            ).filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'resolved',
                Complaint.resolved_at >= start_date,
                Complaint.resolved_at < end_date
            ).group_by('year', 'month').order_by('year', 'month').all()
            
            resolution_counts = []
            
            # Process the resolution trend data
            current_date = start_date
            while current_date < end_date:
                # Find count for this month
                count = 0
                for data in resolution_trend:
                    if data.year == current_date.year and data.month == current_date.month:
                        count = data.count
                        break
                
                resolution_counts.append(count)
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            # Get complaints for the map
            map_complaints = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.latitude.isnot(None),
                Complaint.longitude.isnot(None)
            ).all()

            # Format complaints for GeoJSON
            complaints_geojson = {
                'type': 'FeatureCollection',
                'features': [{
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [complaint.longitude, complaint.latitude]
                    },
                    'properties': {
                        'id': complaint.id,
                        'title': complaint.title,
                        'location': complaint.location,
                        'status': complaint.status,
                        'priority': complaint.priority
                    }
                } for complaint in map_complaints]
            }
            
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
            priority_complaints = []
            trend_dates = []
            trend_counts = []
            resolution_counts = []
            complaints_geojson = {'type': 'FeatureCollection', 'features': []}
        
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
                              priority_complaints=priority_complaints,
                              avg_rating=avg_rating,
                              trend_dates=trend_dates,
                              trend_counts=trend_counts,
                              resolution_counts=resolution_counts,
                              complaints=complaints_geojson)
    
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