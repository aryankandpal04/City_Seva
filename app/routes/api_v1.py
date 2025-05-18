from flask import Blueprint, jsonify, request, current_app
from app import db
from app.models import User, Complaint, Category, ComplaintUpdate, ComplaintMedia, Feedback
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from marshmallow import Schema, fields, ValidationError
from functools import wraps
from datetime import datetime, timedelta
import uuid

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Schema definitions for validation and serialization
class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    full_name = fields.Function(lambda obj: f"{obj.first_name} {obj.last_name}")
    role = fields.Str(dump_only=True)
    department = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str()
    department = fields.Str()

class ComplaintSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    location = fields.Str(required=True)
    latitude = fields.Float()
    longitude = fields.Float()
    status = fields.Str(dump_only=True)
    priority = fields.Str()
    category_id = fields.Int(required=True)
    user_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    resolved_at = fields.DateTime(dump_only=True)
    media_path = fields.Str()
    category = fields.Nested(CategorySchema, dump_only=True)
    updates = fields.List(fields.Nested(lambda: ComplaintUpdateSchema(exclude=('complaint',))), dump_only=True)

class ComplaintUpdateSchema(Schema):
    id = fields.Int(dump_only=True)
    complaint_id = fields.Int(required=True)
    status = fields.Str(required=True)
    comment = fields.Str(required=True)
    user_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    user = fields.Nested(UserSchema, dump_only=True)
    complaint = fields.Nested(lambda: ComplaintSchema(exclude=('updates',)), dump_only=True)

class FeedbackSchema(Schema):
    id = fields.Int(dump_only=True)
    complaint_id = fields.Int(required=True)
    rating = fields.Int(required=True)
    comment = fields.Str()
    created_at = fields.DateTime(dump_only=True)

# Custom decorators for roles
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({"message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

def official_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role not in ['admin', 'official']:
            return jsonify({"message": "Official access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

# API Auth endpoints
@api_v1.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token"""
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400
    
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.verify_password(password):
        return jsonify({"message": "Invalid credentials"}), 401
    
    # Create token with 1 day expiration
    access_token = create_access_token(
        identity=user.id,
        expires_delta=timedelta(days=1)
    )
    
    user_schema = UserSchema()
    user_data = user_schema.dump(user)
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": user_data
    }), 200

@api_v1.route('/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if token is valid and return user data"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    user_schema = UserSchema()
    user_data = user_schema.dump(user)
    
    return jsonify({
        "message": "Token is valid",
        "user": user_data
    }), 200

# Categories
@api_v1.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    categories = Category.query.all()
    category_schema = CategorySchema(many=True)
    
    return jsonify({
        "message": "Categories retrieved successfully",
        "categories": category_schema.dump(categories)
    }), 200

@api_v1.route('/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get a specific category"""
    category = Category.query.get_or_404(category_id)
    category_schema = CategorySchema()
    
    return jsonify({
        "message": "Category retrieved successfully",
        "category": category_schema.dump(category)
    }), 200

# Complaints endpoints
@api_v1.route('/complaints', methods=['GET'])
@jwt_required()
def get_complaints():
    """Get all complaints or filter by query parameters"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Base query
    query = Complaint.query
    
    # Apply filters based on user role
    if user.role == 'citizen':
        # Citizens can only see their own complaints
        query = query.filter_by(user_id=user.id)
    elif user.role == 'official':
        # Officials can see complaints in their department
        categories = Category.query.filter_by(department=user.department).all()
        category_ids = [c.id for c in categories]
        
        if category_ids:
            query = query.filter(Complaint.category_id.in_(category_ids))
        else:
            return jsonify({
                "message": "No categories found for your department",
                "complaints": []
            }), 200
    
    # Apply additional filters from query parameters
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    priority = request.args.get('priority')
    if priority:
        query = query.filter_by(priority=priority)
    
    # Sort by most recent first
    query = query.order_by(Complaint.created_at.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Limit per_page to avoid overloading
    if per_page > 50:
        per_page = 50
    
    complaints_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    complaint_schema = ComplaintSchema(many=True)
    
    return jsonify({
        "message": "Complaints retrieved successfully",
        "complaints": complaint_schema.dump(complaints_paginated.items),
        "pagination": {
            "total_items": complaints_paginated.total,
            "total_pages": complaints_paginated.pages,
            "current_page": complaints_paginated.page,
            "per_page": complaints_paginated.per_page,
            "has_next": complaints_paginated.has_next,
            "has_prev": complaints_paginated.has_prev
        }
    }), 200

@api_v1.route('/complaints/<int:complaint_id>', methods=['GET'])
@jwt_required()
def get_complaint(complaint_id):
    """Get a specific complaint"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check permissions based on role
    if user.role == 'citizen' and complaint.user_id != user.id:
        return jsonify({"message": "Access denied"}), 403
    
    elif user.role == 'official':
        category = Category.query.get(complaint.category_id)
        if category and category.department != user.department:
            return jsonify({"message": "Access denied. This complaint is not in your department"}), 403
    
    complaint_schema = ComplaintSchema()
    
    return jsonify({
        "message": "Complaint retrieved successfully",
        "complaint": complaint_schema.dump(complaint)
    }), 200

@api_v1.route('/complaints', methods=['POST'])
@jwt_required()
def create_complaint():
    """Create a new complaint"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    if user.role != 'citizen':
        return jsonify({"message": "Only citizens can create complaints"}), 403
    
    try:
        complaint_schema = ComplaintSchema(only=('title', 'description', 'location', 'latitude', 'longitude', 'category_id', 'priority'))
        complaint_data = complaint_schema.load(request.json)
        
        # Validate category exists
        category = Category.query.get(complaint_data['category_id'])
        if not category:
            return jsonify({"message": "Invalid category"}), 400
        
        # Create new complaint
        complaint = Complaint(
            title=complaint_data['title'],
            description=complaint_data['description'],
            location=complaint_data['location'],
            latitude=complaint_data.get('latitude'),
            longitude=complaint_data.get('longitude'),
            category_id=complaint_data['category_id'],
            priority=complaint_data.get('priority', 'medium'),
            user_id=user.id,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.session.add(complaint)
        db.session.commit()
        
        return jsonify({
            "message": "Complaint created successfully",
            "complaint": complaint_schema.dump(complaint)
        }), 201
    
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400

@api_v1.route('/complaints/<int:complaint_id>/updates', methods=['GET'])
@jwt_required()
def get_complaint_updates(complaint_id):
    """Get updates for a specific complaint"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check permissions based on role
    if user.role == 'citizen' and complaint.user_id != user.id:
        return jsonify({"message": "Access denied"}), 403
    
    elif user.role == 'official':
        category = Category.query.get(complaint.category_id)
        if category and category.department != user.department:
            return jsonify({"message": "Access denied. This complaint is not in your department"}), 403
    
    updates = ComplaintUpdate.query.filter_by(complaint_id=complaint_id).order_by(ComplaintUpdate.created_at.desc()).all()
    update_schema = ComplaintUpdateSchema(many=True, exclude=('complaint',))
    
    return jsonify({
        "message": "Complaint updates retrieved successfully",
        "updates": update_schema.dump(updates)
    }), 200

@api_v1.route('/complaints/<int:complaint_id>/updates', methods=['POST'])
@jwt_required()
@official_required
def create_complaint_update(complaint_id):
    """Create a new update for a complaint"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if official can update this complaint (department check)
    if user.role == 'official':
        category = Category.query.get(complaint.category_id)
        if category and category.department != user.department:
            return jsonify({"message": "Access denied. This complaint is not in your department"}), 403
    
    try:
        update_schema = ComplaintUpdateSchema(only=('status', 'comment'))
        update_data = update_schema.load(request.json)
        
        # Validate status
        valid_statuses = ['pending', 'in_progress', 'resolved', 'rejected']
        if update_data['status'] not in valid_statuses:
            return jsonify({"message": "Invalid status"}), 400
        
        # Create new update
        update = ComplaintUpdate(
            complaint_id=complaint_id,
            status=update_data['status'],
            comment=update_data['comment'],
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        
        # Update complaint status
        old_status = complaint.status
        complaint.status = update_data['status']
        complaint.updated_at = datetime.utcnow()
        
        # If resolving, set resolved_at date
        if update_data['status'] == 'resolved' and old_status != 'resolved':
            complaint.resolved_at = datetime.utcnow()
        
        # Auto-assign to the current official
        if user.role == 'official' and complaint.assigned_to_id != user.id:
            complaint.assigned_to_id = user.id
            complaint.assigned_at = datetime.utcnow()
        
        db.session.add(update)
        db.session.commit()
        
        return jsonify({
            "message": "Complaint update created successfully",
            "update": update_schema.dump(update)
        }), 201
    
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400

@api_v1.route('/complaints/<int:complaint_id>/feedback', methods=['POST'])
@jwt_required()
def submit_feedback(complaint_id):
    """Submit feedback for a resolved complaint"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    if user.role != 'citizen':
        return jsonify({"message": "Only citizens can submit feedback"}), 403
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if this is the user's complaint
    if complaint.user_id != user.id:
        return jsonify({"message": "Access denied. You can only submit feedback for your own complaints"}), 403
    
    # Check if complaint is resolved
    if complaint.status != 'resolved':
        return jsonify({"message": "Feedback can only be submitted for resolved complaints"}), 400
    
    # Check if feedback already exists
    existing_feedback = Feedback.query.filter_by(complaint_id=complaint_id).first()
    if existing_feedback:
        return jsonify({"message": "Feedback already submitted for this complaint"}), 400
    
    try:
        feedback_schema = FeedbackSchema(only=('rating', 'comment'))
        feedback_data = feedback_schema.load(request.json)
        
        # Validate rating
        if feedback_data['rating'] < 1 or feedback_data['rating'] > 5:
            return jsonify({"message": "Rating must be between 1 and 5"}), 400
        
        # Create new feedback
        feedback = Feedback(
            complaint_id=complaint_id,
            rating=feedback_data['rating'],
            comment=feedback_data.get('comment', ''),
            created_at=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            "message": "Feedback submitted successfully",
            "feedback": feedback_schema.dump(feedback)
        }), 201
    
    except ValidationError as err:
        return jsonify({"message": "Validation error", "errors": err.messages}), 400

# Statistics endpoints
@api_v1.route('/stats/overview', methods=['GET'])
@jwt_required()
def get_stats_overview():
    """Get an overview of complaint statistics"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Base queries
    if user.role == 'citizen':
        # Citizens only see their own stats
        total = Complaint.query.filter_by(user_id=user.id).count()
        pending = Complaint.query.filter_by(user_id=user.id, status='pending').count()
        in_progress = Complaint.query.filter_by(user_id=user.id, status='in_progress').count()
        resolved = Complaint.query.filter_by(user_id=user.id, status='resolved').count()
        rejected = Complaint.query.filter_by(user_id=user.id, status='rejected').count()
    
    elif user.role == 'official':
        # Officials see stats for their department
        categories = Category.query.filter_by(department=user.department).all()
        category_ids = [c.id for c in categories]
        
        if category_ids:
            total = Complaint.query.filter(Complaint.category_id.in_(category_ids)).count()
            pending = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'pending'
            ).count()
            in_progress = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'in_progress'
            ).count()
            resolved = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'resolved'
            ).count()
            rejected = Complaint.query.filter(
                Complaint.category_id.in_(category_ids),
                Complaint.status == 'rejected'
            ).count()
        else:
            total = pending = in_progress = resolved = rejected = 0
    
    else:  # Admin
        # Admins see all stats
        total = Complaint.query.count()
        pending = Complaint.query.filter_by(status='pending').count()
        in_progress = Complaint.query.filter_by(status='in_progress').count()
        resolved = Complaint.query.filter_by(status='resolved').count()
        rejected = Complaint.query.filter_by(status='rejected').count()
    
    return jsonify({
        "message": "Statistics retrieved successfully",
        "stats": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "rejected": rejected,
            "resolution_rate": round((resolved / total) * 100, 1) if total > 0 else 0
        }
    }), 200

# Error handlers
@api_v1.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Resource not found"}), 404

@api_v1.errorhandler(500)
def server_error(error):
    current_app.logger.error(f"Server error: {error}")
    return jsonify({"message": "Internal server error"}), 500 