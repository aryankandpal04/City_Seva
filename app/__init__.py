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
import socket
import ntplib
from time import ctime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail = Mail()
csrf = CSRFProtect()

# Import at the top level
from . import firebase_auth

def nl2br(value):
    """Convert newlines to <br> tags"""
    if not value:
        return ''
    return re.sub(r'\n', '<br>', value)

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
    
    # Initialize Firebase
    if app.config.get('FIREBASE_PROJECT_ID'):
        with app.app_context():
            # Add time synchronization check before initializing Firebase
            try:
                import time
                
                # First try NTP for the most accurate time
                time_offset = 0
                time_sync_success = False
                
                try:
                    ntp_client = ntplib.NTPClient()
                    server_time = time.time()
                    
                    for ntp_server in ['pool.ntp.org', 'time.google.com', 'time.windows.com', 'time.nist.gov']:
                        try:
                            # Use a short timeout to avoid hanging
                            response = ntp_client.request(ntp_server, timeout=1)
                            if response:
                                ntp_time = response.tx_time
                                time_offset = ntp_time - server_time
                                time_diff = abs(time_offset)
                                
                                if time_diff > 60:  # If more than 1 minute difference
                                    app.logger.warning(f"Server time is out of sync by {time_diff:.1f} seconds (NTP server: {ntp_server})")
                                    app.logger.info(f"Setting time offset to {time_offset:.1f} seconds for JWT validation")
                                else:
                                    app.logger.info(f"Server time is in sync (difference: {time_diff:.1f} seconds, NTP server: {ntp_server})")
                                
                                # Store the time offset in the app config for Firebase
                                app.time_offset = time_offset
                                time_sync_success = True
                                break
                        except Exception:
                            continue
                except (ImportError, Exception) as e:
                    # Fall back to HTTP-based time services if NTP fails
                    import requests
                    
                    # Try multiple time servers with fallbacks
                    time_servers = [
                        'http://worldtimeapi.org/api/ip',
                        'http://worldclockapi.com/api/json/utc/now',
                        'http://date.jsontest.com'
                    ]
                    
                    server_time = time.time()
                    
                    for time_server in time_servers:
                        try:
                            response = requests.get(time_server, timeout=1)
                            if response.status_code == 200:
                                time_data = response.json()
                                
                                # Different APIs return time in different formats
                                if 'unixtime' in time_data:  # worldtimeapi.org
                                    ntp_time = time_data.get('unixtime')
                                elif 'currentFileTime' in time_data:  # worldclockapi.com
                                    # Convert Windows file time to Unix time (seconds since 1970)
                                    file_time = int(time_data.get('currentFileTime')) / 10000000 - 11644473600
                                    ntp_time = file_time
                                elif 'milliseconds_since_epoch' in time_data:  # date.jsontest.com
                                    ntp_time = time_data.get('milliseconds_since_epoch') / 1000
                                else:
                                    continue
                                
                                time_offset = ntp_time - server_time
                                time_diff = abs(time_offset)
                                
                                if time_diff > 60:  # If more than 1 minute difference
                                    app.logger.warning(f"Server time is out of sync by {time_diff:.1f} seconds (HTTP server: {time_server})")
                                    app.logger.info(f"Setting time offset to {time_offset:.1f} seconds for JWT validation")
                                else:
                                    app.logger.info(f"Server time is in sync (difference: {time_diff:.1f} seconds, HTTP server: {time_server})")
                                
                                # Store the time offset in the app config for Firebase
                                app.time_offset = time_offset
                                time_sync_success = True
                                break
                        except requests.exceptions.RequestException:
                            continue
                    
                    if not time_sync_success:
                        app.logger.info("Time synchronization check skipped - using system time with extended JWT clock skew tolerance.")
                        app.time_offset = 0
            except Exception as e:
                app.logger.info(f"Time check skipped: {str(e)}. Using extended JWT clock skew tolerance.")
                app.time_offset = 0
                
            # Now initialize Firebase
            firebase_auth.init_app(app)
            app.logger.info("Firebase initialized with time offset handling")
            
            # Set up user loader for Flask-Login with Firebase
            @login_manager.user_loader
            def load_user(user_id):
                """Load user by UID for Flask-Login"""
                return firebase_auth.get_user(user_id)
            
            # Add login/logout event listeners for Firebase
            @user_logged_in.connect_via(app)
            def on_user_logged_in(sender, user):
                if hasattr(user, 'uid'):
                    firebase_auth.update_user(user.uid, is_online=True)
                
            @user_logged_out.connect_via(app)
            def on_user_logged_out(sender, user):
                if user and hasattr(user, 'uid'):
                    firebase_auth.update_user(user.uid, is_online=False)
                
            # Jinja template context processor
            @app.context_processor
            def inject_notifications():
                """Inject notifications data for all templates with Firebase"""
                if current_user.is_authenticated and hasattr(current_user, 'uid'):
                    try:
                        # Retrieve notifications from Firestore
                        unread_notifications = firebase_auth.db.collection('notifications')\
                            .where('user_id', '==', current_user.uid)\
                            .where('is_read', '==', False)\
                            .order_by('created_at', direction='DESCENDING')\
                            .limit(5)\
                            .stream()
                        
                        notifications = list(unread_notifications)
                        unread_count = len(notifications)
                        
                        return {
                            'unread_notifications_count': unread_count, 
                            'recent_unread_notifications': notifications
                        }
                    except Exception as e:
                        app.logger.error(f"Error retrieving notifications: {e}")
                        return {'unread_notifications_count': 0, 'recent_unread_notifications': []}
                return {'unread_notifications_count': 0, 'recent_unread_notifications': []}
    else:
        # Fallback to SQLAlchemy user loader
        from app.models import User
        @login_manager.user_loader
        def load_user(user_id):
            """Load user by ID for Flask-Login"""
            return User.query.get(int(user_id))
        
        # Add login/logout event listeners to track user online status with SQLite
        @user_logged_in.connect_via(app)
        def on_user_logged_in(sender, user):
            user.is_online = True
            db.session.commit()
            
        @user_logged_out.connect_via(app)
        def on_user_logged_out(sender, user):
            if user:
                user.is_online = False
                db.session.commit()
        
        # Jinja template context processor for SQLite
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
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal server error: {e}")
        return render_template('errors/500.html'), 500
    
    # Create database tables (still needed for non-Firebase data)
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
    
    # Add template filters for Firebase compatibility
    @app.template_filter('format_timestamp')
    def format_timestamp(value, format='%Y-%m-%d %H:%M'):
        """Format a timestamp value from Firestore"""
        if value is None:
            return "N/A"
            
        timestamp = None
        
        # If it's a DocumentSnapshot
        if hasattr(value, 'to_dict'):
            doc_dict = value.to_dict()
            if 'created_at' in doc_dict:
                timestamp = doc_dict.get('created_at')
        
        # If it's a dictionary 
        elif isinstance(value, dict) and 'created_at' in value:
            timestamp = value['created_at']
            
        # If it has get method (DocumentSnapshot) but not to_dict
        elif hasattr(value, 'get'):
            try:
                if 'created_at' in value:
                    timestamp = value.get('created_at')
            except (TypeError, AttributeError):
                pass
        else:
            # It might be the timestamp itself
            timestamp = value
        
        # Handle Firebase timestamp
        if hasattr(timestamp, 'timestamp'):
            try:
                return timestamp.timestamp().strftime(format)
            except AttributeError:
                pass
        elif isinstance(timestamp, datetime):
            return timestamp.strftime(format)
            
        return "N/A"
    
    @app.template_filter('get_doc_attr')
    def get_doc_attr(doc, attr, default=""):
        """Get attribute from Firebase document snapshot safely"""
        if doc is None:
            return default
            
        # If it's a dictionary, use regular get method
        if isinstance(doc, dict):
            return doc.get(attr, default)
            
        # If it's a DocumentSnapshot (has to_dict method)
        if hasattr(doc, 'to_dict'):
            # Convert to dictionary first
            doc_dict = doc.to_dict()
            # Add the id if available
            if hasattr(doc, 'id'):
                doc_dict['id'] = doc.id
            return doc_dict.get(attr, default)
            
        # If it has get method but doesn't accept default parameter (DocumentSnapshot)
        if hasattr(doc, 'get'):
            try:
                # Check if field exists in document
                if attr in doc:
                    return doc.get(attr)
                else:
                    return default
            except (TypeError, AttributeError):
                # Fallback for any other errors
                return default
                
        return default
    
    return app 