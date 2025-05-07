from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Complaint, Category, ComplaintUpdate, Feedback, AuditLog
from app.utils.decorators import admin_required, official_required

api = Blueprint('api', __name__)

@api.route('/stats/overview')
@login_required
def stats_overview():
    """API endpoint to get complaint statistics for dashboard"""
    # Count by status
    pending_count = Complaint.query.filter_by(status='pending').count()
    in_progress_count = Complaint.query.filter_by(status='in_progress').count()
    resolved_count = Complaint.query.filter_by(status='resolved').count()
    rejected_count = Complaint.query.filter_by(status='rejected').count()
    
    # If official, filter by department
    if current_user.role == 'official' and current_user.department:
        # Find categories assigned to this department
        category_ids = [c.id for c in Category.query.filter_by(department=current_user.department).all()]
        
        pending_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                            Complaint.status == 'pending').count()
        in_progress_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                                Complaint.status == 'in_progress').count()
        resolved_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                             Complaint.status == 'resolved').count()
        rejected_count = Complaint.query.filter(Complaint.category_id.in_(category_ids), 
                                             Complaint.status == 'rejected').count()
    
    return jsonify({
        'status': 'success',
        'data': {
            'pending': pending_count,
            'in_progress': in_progress_count,
            'resolved': resolved_count,
            'rejected': rejected_count,
            'total': pending_count + in_progress_count + resolved_count + rejected_count
        }
    })

@api.route('/stats/category')
@login_required
def stats_by_category():
    """API endpoint to get complaints by category for charts"""
    # Query to get complaints by category
    from sqlalchemy import func
    
    # Base query
    query = db.session.query(
        Category.name, 
        func.count(Complaint.id)
    ).join(Complaint).group_by(Category.name)
    
    # If official, filter by department
    if current_user.role == 'official' and current_user.department:
        query = query.filter(Category.department == current_user.department)
    
    results = query.all()
    
    return jsonify({
        'status': 'success',
        'data': {
            'labels': [r[0] for r in results],
            'values': [r[1] for r in results]
        }
    })

@api.route('/stats/priority')
@login_required
def stats_by_priority():
    """API endpoint to get complaints by priority for charts"""
    # Query to get complaints by priority
    from sqlalchemy import func
    
    # Base query
    query = db.session.query(
        Complaint.priority, 
        func.count(Complaint.id)
    ).group_by(Complaint.priority)
    
    # If official, filter by department
    if current_user.role == 'official' and current_user.department:
        # Find categories assigned to this department
        category_ids = [c.id for c in Category.query.filter_by(department=current_user.department).all()]
        query = query.filter(Complaint.category_id.in_(category_ids))
    
    results = query.all()
    
    # Format priorities for display
    priorities = {
        'low': 'Low',
        'medium': 'Medium',
        'high': 'High',
        'urgent': 'Urgent'
    }
    
    return jsonify({
        'status': 'success',
        'data': {
            'labels': [priorities.get(r[0], r[0]) for r in results],
            'values': [r[1] for r in results]
        }
    })

@api.route('/stats/timeline')
@login_required
def stats_timeline():
    """API endpoint to get complaint creation timeline for charts"""
    # For simplicity, we'll return fake data
    # In a real app, this would query the database with date filters
    
    data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'datasets': [
            {
                'label': 'New Complaints',
                'data': [12, 19, 3, 5, 2, 3, 20, 33, 23, 12, 5, 6]
            },
            {
                'label': 'Resolved Complaints',
                'data': [7, 11, 5, 8, 3, 7, 15, 25, 20, 10, 6, 2]
            }
        ]
    }
    
    return jsonify({
        'status': 'success',
        'data': data
    })

@api.route('/complaints/<int:complaint_id>/status', methods=['POST'])
@login_required
@official_required
def update_complaint_status(complaint_id):
    """API endpoint to update complaint status"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if the official is authorized to update this complaint
    if current_user.role == 'official' and current_user.department:
        category = Category.query.get(complaint.category_id)
        if category.department != current_user.department:
            return jsonify({
                'status': 'error',
                'message': 'You are not authorized to update this complaint'
            }), 403
    
    # Get data from request
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Status is required'
        }), 400
    
    # Validate status
    new_status = data['status']
    if new_status not in ['pending', 'in_progress', 'resolved', 'rejected']:
        return jsonify({
            'status': 'error',
            'message': 'Invalid status'
        }), 400
    
    # Update complaint status
    old_status = complaint.status
    complaint.status = new_status
    
    # Add complaint update
    comment = data.get('comment', f'Status changed from {old_status} to {new_status}')
    update = ComplaintUpdate(
        complaint_id=complaint.id,
        user_id=current_user.id,
        status=new_status,
        comment=comment
    )
    db.session.add(update)
    
    # Log the action
    log = AuditLog(
        user_id=current_user.id,
        action='update',
        resource_type='complaint',
        resource_id=complaint.id,
        details=f'Updated complaint status to {new_status}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Complaint status updated',
        'data': {
            'complaint_id': complaint.id,
            'new_status': new_status
        }
    })

@api.route('/map/complaints')
def map_data():
    """API endpoint to get complaint data for map view"""
    # Get complaints with location data
    complaints = Complaint.query.filter(
        Complaint.latitude.isnot(None),
        Complaint.longitude.isnot(None)
    ).all()
    
    # Build GeoJSON format
    features = []
    for complaint in complaints:
        # Skip complaints without coordinates
        if not complaint.latitude or not complaint.longitude:
            continue
            
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [complaint.longitude, complaint.latitude]
            },
            'properties': {
                'id': complaint.id,
                'title': complaint.title,
                'status': complaint.status,
                'category': complaint.category.name,
                'priority': complaint.priority,
                'created_at': complaint.created_at.strftime('%Y-%m-%d')
            }
        }
        features.append(feature)
    
    geo_json = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geo_json) 