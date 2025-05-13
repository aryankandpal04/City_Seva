"""
Example file demonstrating how to use Firebase helpers in Flask routes.
This file is for reference only and should not be executed directly.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.firebase_helpers import (
    get_complaints, get_complaint, create_complaint, update_complaint, delete_complaint,
    get_categories, get_complaint_media, create_complaint_media, get_complaint_updates,
    create_complaint_update, create_audit_log, create_notification
)

# Example blueprint
firebase_example = Blueprint('firebase_example', __name__)

@firebase_example.route('/complaints')
@login_required
def complaints():
    """List all complaints using Firebase"""
    # Get parameters
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['COMPLAINTS_PER_PAGE']
    status = request.args.get('status', '')
    category_id = request.args.get('category_id', '')
    search_query = request.args.get('search_query', '')
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get complaints from Firebase
    complaints = get_complaints(
        limit=per_page,
        offset=offset,
        status=status if status else None,
        category_id=category_id if category_id else None,
        search_query=search_query if search_query else None
    )
    
    # Get categories for filter dropdown
    categories = get_categories()
    
    # Return template with data
    return render_template(
        'complaints.html',
        complaints=complaints,
        categories=categories,
        page=page,
        search_query=search_query
    )

@firebase_example.route('/complaint/<complaint_id>')
@login_required
def complaint_detail(complaint_id):
    """View a specific complaint using Firebase"""
    # Get complaint with all related data
    complaint = get_complaint(complaint_id)
    
    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('firebase_example.complaints'))
    
    # Get updates for this complaint
    updates = get_complaint_updates(complaint_id)
    
    return render_template(
        'complaint_detail.html',
        complaint=complaint,
        updates=updates
    )

@firebase_example.route('/complaint/<complaint_id>/update', methods=['POST'])
@login_required
def update_complaint_status(complaint_id):
    """Update a complaint status using Firebase"""
    status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    if not status:
        flash('Status is required.', 'danger')
        return redirect(url_for('firebase_example.complaint_detail', complaint_id=complaint_id))
    
    # Create an update record
    update_data = {
        'complaint_id': complaint_id,
        'user_id': current_user.uid,  # Assuming current_user.uid is the Firebase user ID
        'status': status,
        'comment': comment
    }
    
    # Create the update (this will also update the complaint status)
    update = create_complaint_update(update_data)
    
    if update:
        # Log the action
        create_audit_log({
            'user_id': current_user.uid,
            'action': 'update_status',
            'resource_type': 'complaint',
            'resource_id': complaint_id,
            'details': f'Updated status to {status}',
            'ip_address': request.remote_addr
        })
        
        # Get complaint to find owner
        complaint = get_complaint(complaint_id)
        
        # Notify the complaint owner
        if complaint and complaint.get('user_id') != current_user.uid:
            create_notification({
                'user_id': complaint['user_id'],
                'title': f'Complaint Status Updated',
                'message': f'Your complaint "{complaint["title"]}" has been updated to {status}.'
            })
        
        flash('Complaint status updated successfully.', 'success')
    else:
        flash('Error updating complaint status.', 'danger')
    
    return redirect(url_for('firebase_example.complaint_detail', complaint_id=complaint_id))

@firebase_example.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    """Create a new complaint using Firebase"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        category_id = request.form.get('category_id')
        
        # Validate required fields
        if not all([title, description, location, latitude, longitude, category_id]):
            flash('All fields are required.', 'danger')
            categories = get_categories()
            return render_template('new_complaint.html', categories=categories)
        
        # Prepare complaint data
        complaint_data = {
            'title': title,
            'description': description,
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'category_id': category_id,
            'user_id': current_user.uid,
            'status': 'pending',
            'priority': 'medium'
        }
        
        # Create complaint in Firebase
        complaint = create_complaint(complaint_data)
        
        if complaint:
            # Upload media files if provided
            media_files = request.files.getlist('media')
            
            for media_file in media_files:
                if media_file and media_file.filename:
                    # Determine media type
                    filename = media_file.filename.lower()
                    media_type = 'image'
                    if filename.endswith(('.mp4', '.mov', '.avi', '.wmv')):
                        media_type = 'video'
                    
                    # Generate a unique filename
                    import uuid
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    # Upload to Firebase Storage
                    storage_path = f"complaints/{complaint['id']}/{unique_filename}"
                    file_url = current_app.firebase_db.upload_file(media_file, storage_path)
                    
                    if file_url:
                        # Create media entry in Firestore
                        media_data = {
                            'complaint_id': complaint['id'],
                            'file_url': file_url,
                            'storage_path': storage_path,
                            'media_type': media_type
                        }
                        create_complaint_media(media_data)
            
            # Log the action
            create_audit_log({
                'user_id': current_user.uid,
                'action': 'create',
                'resource_type': 'complaint',
                'resource_id': complaint['id'],
                'details': f'Created new complaint: {title}',
                'ip_address': request.remote_addr
            })
            
            flash('Complaint submitted successfully.', 'success')
            return redirect(url_for('firebase_example.complaint_detail', complaint_id=complaint['id']))
        else:
            flash('Error submitting complaint.', 'danger')
    
    # GET request - render form
    categories = get_categories()
    return render_template('new_complaint.html', categories=categories)

@firebase_example.route('/complaint/<complaint_id>/delete', methods=['POST'])
@login_required
def delete_complaint_route(complaint_id):
    """Delete a complaint using Firebase"""
    # Get the complaint first to check ownership
    complaint = get_complaint(complaint_id)
    
    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('firebase_example.complaints'))
    
    # Check if user is admin or the complaint owner
    if current_user.role != 'admin' and complaint.get('user_id') != current_user.uid:
        flash('You do not have permission to delete this complaint.', 'danger')
        return redirect(url_for('firebase_example.complaint_detail', complaint_id=complaint_id))
    
    # Delete the complaint and related data
    if delete_complaint(complaint_id):
        # Log the action
        create_audit_log({
            'user_id': current_user.uid,
            'action': 'delete',
            'resource_type': 'complaint',
            'resource_id': complaint_id,
            'details': f'Deleted complaint: {complaint.get("title", "Unknown")}',
            'ip_address': request.remote_addr
        })
        
        flash('Complaint has been deleted.', 'success')
        return redirect(url_for('firebase_example.complaints'))
    else:
        flash('Error deleting complaint.', 'danger')
        return redirect(url_for('firebase_example.complaint_detail', complaint_id=complaint_id)) 