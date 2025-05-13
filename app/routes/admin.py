from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func, desc, case
from app import db, firebase_auth, firebase_db
from firebase_admin import firestore
from app.models import User, Complaint, Category, ComplaintUpdate, Feedback, AuditLog, Notification, OfficialRequest, ComplaintMedia
from app.forms import ComplaintUpdateForm, SearchForm
from app.utils.email import send_complaint_notification
from app.utils.decorators import admin_required, official_required
from functools import wraps

admin = Blueprint('admin', __name__)

# FirestorePagination class for Firebase pagination
class FirestorePagination:
    """Class to mimic SQLAlchemy pagination for Firestore queries"""
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
    
    @property
    def pages(self):
        return (self.total + self.per_page - 1) // self.per_page
    
    @property
    def has_prev(self):
        return self.page > 1
    
    @property
    def has_next(self):
        return self.page < self.pages
        
    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None
        
    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None
    
    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

# Helper function for fetching user information for Firebase complaints
def fetch_user_info_for_complaint(complaint_data):
    """Helper to fetch and add user information to Firebase complaint data"""
    try:
        if 'user_id' in complaint_data and complaint_data['user_id']:
            user_id = complaint_data['user_id']
            current_app.logger.info(f"Fetching user info for user_id: {user_id}")
            
            user_doc = firebase_auth.db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                # Add debug logging
                current_app.logger.info(f"Found user data: {user_data}")
                
                # Set user name from first and last name, or from display_name, or from email
                if 'first_name' in user_data and 'last_name' in user_data:
                    complaint_data['user_name'] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                elif 'display_name' in user_data and user_data['display_name']:
                    complaint_data['user_name'] = user_data['display_name']
                elif 'email' in user_data:
                    complaint_data['user_name'] = user_data['email']
                else:
                    complaint_data['user_name'] = f"User {user_id}"
                
                # Set other user fields
                complaint_data['user_email'] = user_data.get('email', 'No email')
                complaint_data['user_phone'] = user_data.get('phone', 'Not provided')
                complaint_data['user_address'] = user_data.get('address', 'Not provided')
                complaint_data['user_username'] = user_data.get('username', 'Not available')
                
                # Format created_at if it's a timestamp
                if 'created_at' in user_data:
                    if hasattr(user_data['created_at'], 'strftime'):
                        complaint_data['user_created_at'] = user_data['created_at'].strftime('%Y-%m-%d')
                    else:
                        complaint_data['user_created_at'] = str(user_data['created_at'])
                else:
                    complaint_data['user_created_at'] = 'Unknown'
            else:
                current_app.logger.warning(f"User document not found for user_id: {user_id}")
                complaint_data['user_name'] = f"Unknown User (ID: {user_id})"
        else:
            current_app.logger.warning(f"No user_id found in complaint data: {complaint_data}")
    except Exception as e:
        current_app.logger.error(f"Error getting user information: {e}")
        # Add basic user info even if there's an error
        complaint_data['user_name'] = 'Error retrieving user'
        complaint_data['user_email'] = 'Error'
    
    return complaint_data

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
    # Get complaint stats from Firebase
    try:
        # Count complaints by status
        complaints_ref = firebase_auth.db.collection('complaints')
        
        # Get counts for each status
        total_complaints = 0
        pending_count = 0
        in_progress_count = 0
        resolved_count = 0
        rejected_count = 0
        
        # Get all complaints and count by status
        complaints = list(complaints_ref.stream())
        total_complaints = len(complaints)
        
        for complaint_doc in complaints:
            complaint = complaint_doc.to_dict()
            status = complaint.get('status', 'pending')
            if status == 'pending':
                pending_count += 1
            elif status == 'in_progress':
                in_progress_count += 1
            elif status == 'resolved':
                resolved_count += 1
            elif status == 'rejected':
                rejected_count += 1
        
        # Get recent complaints
        recent_complaints_docs = list(complaints_ref.order_by('created_at', direction='DESCENDING').limit(5).stream())
        # Convert to dictionaries and add id
        recent_complaints = []
        for doc in recent_complaints_docs:
            complaint_data = doc.to_dict()
            complaint_data['id'] = doc.id
            
            # Add category name for Firebase complaints since they don't have relations
            try:
                if 'category_id' in complaint_data:
                    category_doc = firebase_auth.db.collection('categories').document(complaint_data['category_id']).get()
                    if category_doc.exists:
                        category_data = category_doc.to_dict()
                        complaint_data['category_name'] = category_data.get('name', 'Unknown')
                    else:
                        complaint_data['category_name'] = 'Unknown'
                else:
                    complaint_data['category_name'] = 'No Category'
            except Exception as e:
                current_app.logger.error(f"Error fetching category: {e}")
                complaint_data['category_name'] = 'Error'
            
            # Add user information
            complaint_data = fetch_user_info_for_complaint(complaint_data)
                
            recent_complaints.append(complaint_data)
        
        # Get user stats
        users_ref = firebase_auth.db.collection('users')
        users = list(users_ref.stream())
        total_users = len(users)
        citizen_count = 0
        official_count = 0
        
        for user_doc in users:
            user = user_doc.to_dict()
            role = user.get('role', 'citizen')
            if role == 'citizen':
                citizen_count += 1
            elif role == 'official':
                official_count += 1
        
        # Get online users
        online_users_docs = list(users_ref.where('is_online', '==', True).stream())
        online_count = len(online_users_docs)
        
        # Get officials
        officials_docs = list(users_ref.where('role', '==', 'official').stream())
        # Convert to dictionaries and add id
        officials = []
        for doc in officials_docs:
            official_data = doc.to_dict()
            official_data['id'] = doc.id
            officials.append(official_data)
        
        # Count pending official requests
        official_requests_count = 0
        if current_user.role == 'admin':
            try:
                official_requests_docs = list(firebase_auth.db.collection('official_requests')
                                          .where('status', '==', 'pending')
                                          .stream())
                official_requests_count = len(official_requests_docs)
            except Exception as e:
                current_app.logger.error(f"Error getting official requests: {e}")
    
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
                              online_count=online_count,
                              officials=officials,
                              official_requests_count=official_requests_count)
    except Exception as e:
        current_app.logger.error(f"Firebase error: {e}")
        flash('Error retrieving dashboard data', 'danger')
        return render_template('admin/dashboard.html', official_requests_count=0)

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
    """View and update a specific complaint"""
    # Check if we're using Firebase (string ID)
    if isinstance(complaint_id, str) and not complaint_id.isdigit() and hasattr(firebase_auth, 'db'):
        try:
            # Get complaint data from Firestore
            complaint_ref = firebase_auth.db.collection('complaints').document(complaint_id)
            complaint_doc = complaint_ref.get()
            
            if not complaint_doc.exists:
                flash('Complaint not found in Firebase.', 'danger')
                return redirect(url_for('admin.complaints'))
            
            # Convert to dict and add ID
            complaint_data = complaint_doc.to_dict()
            complaint_data['id'] = complaint_id
            
            # Get category name
            try:
                if 'category_id' in complaint_data:
                    category_doc = firebase_auth.db.collection('categories').document(complaint_data['category_id']).get()
                    if category_doc.exists:
                        category_data = category_doc.to_dict()
                        complaint_data['category_name'] = category_data.get('name', 'Unknown')
                    else:
                        complaint_data['category_name'] = 'Unknown'
            except Exception as e:
                current_app.logger.error(f"Error getting category: {e}")
            
            # Get user information
            complaint_data = fetch_user_info_for_complaint(complaint_data)
            
            # Use SQL Alchemy form for now, we'll render a simplified version in the template
            form = ComplaintUpdateForm()
            
            # Initialize form with empty choices to prevent "NoneType is not iterable" error
            form.assigned_to_id.choices = [(0, 'Unassigned')]
            
            # Pass empty updates list to prevent another potential "NoneType is not iterable" error
            updates = []
            
            return render_template('admin/complaint_detail.html',
                                complaint=complaint_data,
                                form=form,
                                updates=updates)
                                
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash('Error retrieving complaint from Firebase', 'danger')
            return redirect(url_for('admin.complaints'))
    
    # Continue with SQL Alchemy version for integer IDs
    try:
        complaint_id_int = int(complaint_id)
        complaint = Complaint.query.get_or_404(complaint_id_int)
    except ValueError:
        flash('Invalid complaint ID.', 'danger')
        return redirect(url_for('admin.complaints'))
    
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
    """Manage users"""
    role_filter = request.args.get('role', '')
    
    # Check if Firebase is enabled
    if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
        try:
            # Use Firebase for data retrieval
            users_ref = firebase_auth.db.collection('users')
            
            # Apply role filter if provided
            if role_filter in ['citizen', 'official', 'admin']:
                users_query = users_ref.where('role', '==', role_filter)
            else:
                users_query = users_ref
                
            # Get users
            user_docs = list(users_query.order_by('created_at', direction='DESCENDING').stream())
            users = []
            
            for doc in user_docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                users.append(user_data)
                
            return render_template('admin/users.html', users=users, firebase_enabled=True)
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash(f"Error retrieving users from Firebase: {e}", 'danger')
            return render_template('admin/users.html', users=[], firebase_enabled=True)
    else:
        # Use SQLite for data retrieval
        query = User.query
        
        if role_filter in ['citizen', 'official', 'admin']:
            query = query.filter_by(role=role_filter)
        
        users = query.order_by(User.created_at.desc()).all()
        
        return render_template('admin/users.html', users=users, firebase_enabled=False)

@admin.route('/user/<string:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle a user's active status"""
    # Check if Firebase is enabled
    if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
        try:
            # Use Firebase Admin SDK
            user_ref = firebase_auth.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                flash('User not found.', 'danger')
                return redirect(url_for('admin.users'))
                
            user_data = user_doc.to_dict()
            
            # Don't allow deactivating yourself
            if user_id == current_user.uid:
                flash('You cannot deactivate your own account.', 'danger')
                return redirect(url_for('admin.users'))
            
            # Toggle is_active status
            new_status = not user_data.get('is_active', True)
            
            # Update Firebase Auth user (disabled property)
            try:
                firebase_auth.auth.update_user(
                    user_id,
                    disabled=not new_status  # disabled is the opposite of is_active
                )
            except Exception as e:
                current_app.logger.error(f"Firebase Auth error: {e}")
                flash(f"Error updating user in Firebase Auth: {e}", 'danger')
                return redirect(url_for('admin.users'))
            
            # Update Firestore user document
            user_ref.update({
                'is_active': new_status,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Log action
            firebase_auth.create_audit_log(
                current_user.uid,
                'toggle_active',
                'user',
                user_id,
                f'Set user active status to {new_status}',
                request.remote_addr
            )
            
            status = 'activated' if new_status else 'deactivated'
            flash(f'User has been {status}.', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash(f"Error toggling user status: {e}", 'danger')
            
        return redirect(url_for('admin.users'))
    else:
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
    
    # Check if Firebase is enabled
    if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
        try:
            # Update user in Firestore
            user_ref = firebase_auth.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                flash('User not found.', 'danger')
                return redirect(url_for('admin.users'))
            
            # Update user data
            user_ref.update({
                'role': 'official',
                'department': department,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Log action
            firebase_auth.create_audit_log(
                current_user.uid,
                'role_change',
                'user',
                user_id,
                f'Changed user role to official in {department} department',
                request.remote_addr
            )
            
            flash('User has been promoted to official.', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash(f"Error promoting user: {e}", 'danger')
            
        return redirect(url_for('admin.users'))
    else:
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
    # Check if Firebase is enabled
    if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
        try:
            # Update user in Firestore
            user_ref = firebase_auth.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                flash('User not found.', 'danger')
                return redirect(url_for('admin.users'))
            
            # Update user data
            user_ref.update({
                'role': 'admin',
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Log action
            firebase_auth.create_audit_log(
                current_user.uid,
                'role_change',
                'user',
                user_id,
                'Changed user role to admin',
                request.remote_addr
            )
            
            flash('User has been promoted to admin.', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash(f"Error promoting user: {e}", 'danger')
            
        return redirect(url_for('admin.users'))
    else:
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
    # Check if Firebase is enabled
    if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
        try:
            # Check for confirmation
            if not request.form.get('confirm'):
                flash('Please confirm the deletion.', 'warning')
                return redirect(url_for('admin.users'))
            
            # Get user data before deletion
            user_ref = firebase_auth.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                flash('User not found.', 'danger')
                return redirect(url_for('admin.users'))
            
            user_data = user_doc.to_dict()
            
            # Don't allow deleting yourself
            if user_id == current_user.uid:
                flash('You cannot delete your own account.', 'danger')
                return redirect(url_for('admin.users'))
            
            # Log action before deletion
            firebase_auth.create_audit_log(
                current_user.uid,
                'delete_user',
                'user',
                user_id,
                f'Deleted user: {user_data.get("email")}',
                request.remote_addr
            )
            
            # Delete dependencies
            try:
                batch = firebase_auth.db.batch()
                
                # 1. Delete user's complaints
                complaints_query = firebase_auth.db.collection('complaints').where('user_id', '==', user_id)
                complaints = list(complaints_query.stream())
                
                for complaint_doc in complaints:
                    # Get complaint updates for this complaint
                    updates_query = firebase_auth.db.collection('complaint_updates').where('complaint_id', '==', complaint_doc.id)
                    updates = list(updates_query.stream())
                    
                    # Delete updates
                    for update_doc in updates:
                        batch.delete(update_doc.reference)
                    
                    # Delete feedback
                    feedback_query = firebase_auth.db.collection('feedbacks').where('complaint_id', '==', complaint_doc.id)
                    feedback_docs = list(feedback_query.stream())
                    
                    for feedback_doc in feedback_docs:
                        batch.delete(feedback_doc.reference)
                    
                    # Delete complaint
                    batch.delete(complaint_doc.reference)
                
                # 2. Delete user's notifications
                notifications_query = firebase_auth.db.collection('notifications').where('user_id', '==', user_id)
                notifications = list(notifications_query.stream())
                
                for notification_doc in notifications:
                    batch.delete(notification_doc.reference)
                
                # 3. Delete official requests
                requests_query = firebase_auth.db.collection('official_requests').where('user_id', '==', user_id)
                requests = list(requests_query.stream())
                
                for request_doc in requests:
                    batch.delete(request_doc.reference)
                
                # 4. Update official requests where user is reviewer
                reviewer_requests_query = firebase_auth.db.collection('official_requests').where('reviewed_by', '==', user_id)
                reviewer_requests = list(reviewer_requests_query.stream())
                
                for request_doc in reviewer_requests:
                    batch.update(request_doc.reference, {
                        'reviewed_by': None
                    })
                
                # 5. Finally delete the user document
                batch.delete(user_ref)
                
                # Commit all changes in batch
                batch.commit()
                
                # Delete from Firebase Auth
                try:
                    firebase_auth.auth.delete_user(user_id)
                except Exception as e:
                    # If the user doesn't exist in Firebase Auth, we can ignore this error
                    # since we've already deleted the user from Firestore
                    current_app.logger.warning(f"Firebase Auth delete error (continuing anyway): {e}")
                
                flash('User has been permanently deleted.', 'success')
                
            except Exception as e:
                current_app.logger.error(f"Firebase batch operation error: {e}")
                flash(f"Error deleting user dependencies: {e}", 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Firebase error: {e}")
            flash(f"Error deleting user: {e}", 'danger')
            
        return redirect(url_for('admin.users'))
    else:
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
                message=f'Your request for an official account has been approved. You now have official privileges for the {official_request.department} department.'
            )
            db.session.add(notification)
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
            return redirect(url_for('admin.dashboard'))
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
        # Check if using Firebase
        if hasattr(firebase_auth, 'db') and firebase_auth.db is not None:
            # Get complaint data from Firestore
            complaint_ref = firebase_auth.db.collection('complaints').document(complaint_id_str)
            complaint_doc = complaint_ref.get()
            
            if not complaint_doc.exists:
                current_app.logger.warning(f"Complaint {complaint_id} not found in Firestore but exists in SQLite. Proceeding with SQLite deletion only.")
            else:
                # Create a batch operation
                batch = firebase_auth.db.batch()
                
                # 1. Delete all updates for this complaint
                updates_query = firebase_auth.db.collection('complaint_updates').where('complaint_id', '==', complaint_id_str)
                updates = list(updates_query.stream())
                for update_doc in updates:
                    batch.delete(update_doc.reference)
                
                # 2. Delete feedback for this complaint (if any)
                feedbacks_query = firebase_auth.db.collection('feedbacks').where('complaint_id', '==', complaint_id_str)
                feedbacks = list(feedbacks_query.stream())
                for feedback_doc in feedbacks:
                    batch.delete(feedback_doc.reference)
                
                # 3. Delete all media attachments for this complaint
                try:
                    firebase_db.delete_complaint_media_for_complaint(complaint_id_str)
                except Exception as e:
                    current_app.logger.warning(f"Could not delete media attachments: {e}")
                
                # 4. Delete notifications related to this complaint
                try:
                    notifications_query = firebase_auth.db.collection('notifications').where('complaint_id', '==', complaint_id_str)
                    notifications = list(notifications_query.stream())
                    for notification_doc in notifications:
                        batch.delete(notification_doc.reference)
                except Exception as e:
                    current_app.logger.warning(f"Could not delete notifications by complaint_id: {e}")
                    try:
                        notifications_query = firebase_auth.db.collection('notifications').where('resource_id', '==', complaint_id_str)
                        notifications = list(notifications_query.stream())
                        for notification_doc in notifications:
                            batch.delete(notification_doc.reference)
                    except Exception as e:
                        current_app.logger.warning(f"Could not delete notifications by resource_id: {e}")
                
                # 5. Delete the complaint document
                batch.delete(complaint_ref)
                
                # 6. Create audit log entry
                firebase_db.create_audit_log({
                    'user_id': str(current_user.id),
                    'action': 'delete_complaint',
                    'resource_type': 'complaint',
                    'resource_id': complaint_id_str,
                    'details': f'Deleted complaint: {complaint_title} (ID: {complaint_id})',
                    'ip_address': request.remote_addr
                })
                
                # Commit all changes
                batch.commit()
        
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