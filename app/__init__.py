from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mailman import Mail
from config import config
from app.utils.context_processors import inject_now
import re

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Configure login settings
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

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
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Register context processors
    app.context_processor(inject_now)
    
    # Register Jinja2 filters
    app.jinja_env.filters['nl2br'] = nl2br
    
    # Ensure upload directory exists
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.routes.citizen import citizen as citizen_blueprint
    app.register_blueprint(citizen_blueprint)
    
    from app.routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    from app.routes.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 