import os
from dotenv import load_dotenv

# Load environment variables from cityseva.env file
load_dotenv('cityseva.env')

class Config:
    # Application configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development-only'
    BASE_URL = os.environ.get('BASE_URL') or 'http://localhost:5000'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///cityseva.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Firebase Configuration
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')
    FIREBASE_MEASUREMENT_ID = os.environ.get('FIREBASE_MEASUREMENT_ID')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL')
    FIREBASE_SERVICE_ACCOUNT_KEY = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase_service_account.json')
    
    # Use Firebase as primary data store
    USE_FIREBASE = os.environ.get('USE_FIREBASE', 'True').lower() in ('true', '1', 't')
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USE_SSL = False  # Use TLS instead of SSL for better compatibility
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@cityseva.com'
    MAIL_KEYFILE = None  # Disable keyfile for compatibility with Python 3.12
    MAIL_CERTFILE = None  # Disable certfile for compatibility with Python 3.12
    
    # Firebase Email Function (for email fallback)
    FIREBASE_EMAIL_FUNCTION_URL = os.environ.get('FIREBASE_EMAIL_FUNCTION_URL')
    FIREBASE_EMAIL_API_KEY = os.environ.get('FIREBASE_EMAIL_API_KEY')
    
    # OTP configuration
    OTP_LENGTH = int(os.environ.get('OTP_LENGTH') or 6)
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES') or 10)
    OTP_MAX_ATTEMPTS = int(os.environ.get('OTP_MAX_ATTEMPTS') or 5)
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload
    
    # Pagination
    COMPLAINTS_PER_PAGE = 10
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyD8atpL2upxvA99KrVaZFlv8XxgrqbGZGE')
    
    # Authentication configuration
    REQUIRE_EMAIL_VERIFICATION = os.environ.get('REQUIRE_EMAIL_VERIFICATION', 'True').lower() in ('true', '1', 't')
    MAX_FAILED_LOGIN_ATTEMPTS = int(os.environ.get('MAX_FAILED_LOGIN_ATTEMPTS') or 5)
    ACCOUNT_LOCKOUT_MINUTES = int(os.environ.get('ACCOUNT_LOCKOUT_MINUTES') or 30)
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # Use in-memory database for testing
    WTF_CSRF_ENABLED = False
    REQUIRE_EMAIL_VERIFICATION = False
    USE_FIREBASE = False  # Disable Firebase for tests


class ProductionConfig(Config):
    DEBUG = False
    # Use a strong secret key in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Configure proper database in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Use Firebase in production by default
    USE_FIREBASE = os.environ.get('USE_FIREBASE', 'True').lower() in ('true', '1', 't')
    
    # Configure SSL for production
    SSL_REDIRECT = True

    # Production-specific settings
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 