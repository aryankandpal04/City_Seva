from flask import Flask, render_template, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mailman import Mail
from flask_migrate import Migrate
from config import config
from app.utils.context_processors import inject_now
import re
import os
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import desc
from flask_login import user_logged_in, user_logged_out
from datetime import datetime
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail()
csrf = CSRFProtect()

def nl2br(value):
    """Convert newlines to <br> tags"""
    if not value:
        return ''
    return re.sub(r'\n', '<br>', value)

def get_doc_attr(obj, attr, default=''):
    """Get an attribute from an object, with a default value if not present.
    This replaces the Firebase document attribute accessor with a SQLAlchemy model compatible version.
    """
    if obj is None:
        return default
    
    try:
        # Try to access as a SQLAlchemy model attribute
        return getattr(obj, attr, default)
    except:
        # If that fails, try to access as a dictionary key
        try:
            return obj.get(attr, default)
        except:
            return default

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Patch Flask-Mailman for Python 3.12 compatibility
    with app.app_context():
        try:
            from app.utils.smtp_patch import patch_flask_mailman
            patch_result = patch_flask_mailman()
            if patch_result:
                app.logger.info("Flask-Mailman patched successfully for Python 3.12 compatibility")
            else:
                app.logger.warning("Failed to patch Flask-Mailman for Python 3.12 compatibility")
        except Exception as e:
            app.logger.error(f"Error applying Flask-Mailman patch: {e}")
    
    # Now initialize mail after patching
    mail.init_app(app)
    
    # Set up user loader for SQLite
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        try:
            # Try to convert to integer (SQLite IDs)
            return User.query.get(int(user_id))
        except ValueError:
            app.logger.warning(f"Invalid user ID format: {user_id}")
            return None
        
    # Add login/logout event listeners to track user online status
    @user_logged_in.connect_via(app)
    def on_user_logged_in(sender, user):
        user.is_online = True
        user.last_login = datetime.utcnow()
        db.session.commit()
            
    @user_logged_out.connect_via(app)
    def on_user_logged_out(sender, user):
        if user:
            user.is_online = False
            db.session.commit()
        
    # Context processor for notifications
    @app.context_processor
    def inject_notifications():
        """Inject notifications data for all templates"""
        if current_user.is_authenticated:
            from app.models import Notification
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            recent_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                                            .order_by(desc(Notification.created_at))\
                                            .limit(5).all()
            return {'unread_notifications_count': unread_count, 
                    'recent_unread_notifications': recent_notifications}
        return {'unread_notifications_count': 0, 'recent_unread_notifications': []}
    
    # Register context processors
    app.context_processor(inject_now)
    
    # Add config to all templates
    @app.context_processor
    def inject_config():
        return {'config': app.config}
    
    # Add departments to all templates
    @app.context_processor
    def inject_constants():
        from app.utils.constants import DEPARTMENTS, DEPARTMENTS_WITH_EMPTY
        return {
            'departments': [dept[0] for dept in DEPARTMENTS],
            'department_choices': DEPARTMENTS,
            'department_choices_with_empty': DEPARTMENTS_WITH_EMPTY
        }
    
    # Register Jinja2 filters
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['get_doc_attr'] = get_doc_attr
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.routes.citizen import citizen as citizen_blueprint
    app.register_blueprint(citizen_blueprint)
    
    from app.routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    from app.routes.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.routes.government_officials import government_officials as government_officials_blueprint
    app.register_blueprint(government_officials_blueprint, url_prefix='/government-officials')
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal server error: {e}")
        return render_template('errors/500.html'), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Set up logging
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/cityseva.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CitySeva startup')
    
    # Helper template filter for timestamps
    @app.template_filter('format_timestamp')
    def format_timestamp(value, format='%Y-%m-%d %H:%M'):
        """Format a timestamp"""
        if value is None:
            return "N/A"
        
        # Try accessing the attribute if it's an object
        if hasattr(value, 'created_at'):
            timestamp = value.created_at
        else:
            timestamp = value
            
        if isinstance(timestamp, datetime):
            return timestamp.strftime(format)
            
        return "N/A"
    
    return app 