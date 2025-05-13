from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from app import db, login_manager

class User(UserMixin, db.Model):
    """User model for both citizens and government officials"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='citizen')  # citizen, official, admin
    department = db.Column(db.String(64), nullable=True)  # for officials only
    is_active = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)  # Track if user is currently logged in
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='author', lazy='dynamic', 
                                foreign_keys='Complaint.user_id')
    assigned_complaints = db.relationship('Complaint', backref='assigned_to', lazy='dynamic', 
                                         foreign_keys='Complaint.assigned_to_id')
    updates = db.relationship('ComplaintUpdate', backref='user', lazy='dynamic')
    feedbacks = db.relationship('Feedback', backref='user', lazy='dynamic')
    
    @property
    def password(self):
        """Prevent password from being read"""
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self, expiration=3600):
        """Generate token for password reset"""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'reset': self.id})
    
    @staticmethod
    def verify_reset_token(token):
        """Verify reset token"""
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=3600)
        except:
            return None
        return User.query.get(data.get('reset'))
    
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    """Category model for complaint categories"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    department = db.Column(db.String(64))  # Which department handles this category
    icon = db.Column(db.String(64))  # Icon class (for UI)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Complaint(db.Model):
    """Complaint model for citizen complaints"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(256), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, resolved, rejected
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    media_path = db.Column(db.String(256), nullable=True)  # Legacy field, kept for backward compatibility
    media_type = db.Column(db.String(10), nullable=True)   # Legacy field, kept for backward compatibility
    
    # Relationships
    updates = db.relationship('ComplaintUpdate', backref='complaint', lazy='dynamic')
    feedback = db.relationship('Feedback', backref='complaint', uselist=False)
    media_attachments = db.relationship('ComplaintMedia', backref='complaint', lazy='dynamic')
    
    def __repr__(self):
        return f'<Complaint {self.id}>'
    
    @property
    def days_open(self):
        """Calculate days the complaint has been open"""
        if self.status == 'resolved':
            return (self.resolved_at - self.created_at).days
        else:
            return (datetime.utcnow() - self.created_at).days


class ComplaintUpdate(db.Model):
    """Model for tracking updates to complaints"""
    __tablename__ = 'complaint_updates'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ComplaintUpdate {self.id}>'


class Feedback(db.Model):
    """Feedback model for citizens to rate resolved complaints"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Feedback {self.id}>'


class AuditLog(db.Model):
    """Audit log for important system events"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)  # e.g., 'complaint', 'user'
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.id}>'


class Notification(db.Model):
    """Notification model for system notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Notification {self.id}>'


class OfficialRequest(db.Model):
    """Model for tracking requests to become a government official"""
    __tablename__ = 'official_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department = db.Column(db.String(64), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    office_phone = db.Column(db.String(20), nullable=False)
    justification = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='official_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_requests')
    
    def __repr__(self):
        return f'<OfficialRequest {self.id}>'


class ComplaintMedia(db.Model):
    """Model for storing multiple media attachments for complaints"""
    __tablename__ = 'complaint_media'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    file_path = db.Column(db.String(256), nullable=False)
    media_type = db.Column(db.String(10), nullable=False)  # 'image' or 'video'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ComplaintMedia {self.id}>' 