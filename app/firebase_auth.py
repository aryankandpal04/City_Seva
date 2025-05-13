import firebase_admin
from firebase_admin import auth, credentials, firestore
from flask import current_app, session, g
from flask_login import UserMixin
from functools import wraps
import json
import time
from datetime import datetime

# Firebase instance
firebase_app = None
db = None
# Time offset between server and NTP (in seconds)
time_offset = 0

class FirebaseAuthError(Exception):
    """Exception raised for Firebase Authentication errors"""
    pass

class FirebaseUser(UserMixin):
    """User class for Flask-Login that uses Firebase Auth"""
    
    def __init__(self, uid, email, display_name=None, phone_number=None, 
                 role='citizen', department=None, firebase_data=None, is_active=True):
        self.id = uid
        self.uid = uid
        self.email = email
        self.display_name = display_name
        self.phone_number = phone_number
        self.role = role
        self.department = department
        self.email_verified = False
        self._is_active = is_active
        self.firebase_data = firebase_data or {}
        self.last_login = datetime.now()
        self.created_at = datetime.now()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value
        # Update in Firestore if the user is already created
        if hasattr(self, 'uid') and self.uid and db is not None:
            try:
                db.collection('users').document(self.uid).update({
                    'is_active': value
                })
                # Update in Firebase Auth (disabled is the opposite of is_active)
                auth.update_user(self.uid, disabled=not value)
            except Exception as e:
                if current_app:
                    current_app.logger.error(f"Error updating is_active: {e}")
                else:
                    print(f"Error updating is_active: {e}")
        
    # Compatibility properties to match SQLite User model
    @property
    def first_name(self):
        if self.firebase_data and 'first_name' in self.firebase_data:
            return self.firebase_data.get('first_name')
        if self.display_name and ' ' in self.display_name:
            return self.display_name.split(' ')[0]
        return self.display_name or ''
        
    @first_name.setter
    def first_name(self, value):
        if not self.firebase_data:
            self.firebase_data = {}
        self.firebase_data['first_name'] = value
        # If we have UID, update in Firestore
        if hasattr(self, 'uid') and self.uid:
            try:
                db.collection('users').document(self.uid).update({'first_name': value})
            except Exception as e:
                current_app.logger.error(f"Error updating first_name: {e}")
    
    @property
    def last_name(self):
        if self.firebase_data and 'last_name' in self.firebase_data:
            return self.firebase_data.get('last_name')
        if self.display_name and ' ' in self.display_name:
            return ' '.join(self.display_name.split(' ')[1:])
        return ''
        
    @last_name.setter
    def last_name(self, value):
        if not self.firebase_data:
            self.firebase_data = {}
        self.firebase_data['last_name'] = value
        # If we have UID, update in Firestore
        if hasattr(self, 'uid') and self.uid:
            try:
                db.collection('users').document(self.uid).update({'last_name': value})
            except Exception as e:
                current_app.logger.error(f"Error updating last_name: {e}")
    
    @property
    def phone(self):
        if self.firebase_data and 'phone' in self.firebase_data:
            return self.firebase_data.get('phone')
        return self.phone_number or ''
        
    @phone.setter
    def phone(self, value):
        if not self.firebase_data:
            self.firebase_data = {}
        self.firebase_data['phone'] = value
        # If we have UID, update in Firestore
        if hasattr(self, 'uid') and self.uid:
            try:
                db.collection('users').document(self.uid).update({'phone': value})
            except Exception as e:
                current_app.logger.error(f"Error updating phone: {e}")
    
    @property
    def address(self):
        if self.firebase_data and 'address' in self.firebase_data:
            return self.firebase_data.get('address')
        return ''
        
    @address.setter
    def address(self, value):
        if not self.firebase_data:
            self.firebase_data = {}
        self.firebase_data['address'] = value
        # If we have UID, update in Firestore
        if hasattr(self, 'uid') and self.uid:
            try:
                db.collection('users').document(self.uid).update({'address': value})
            except Exception as e:
                current_app.logger.error(f"Error updating address: {e}")
    
    @property
    def username(self):
        """Get username from firebase data"""
        if self.firebase_data and 'username' in self.firebase_data:
            return self.firebase_data.get('username')
        # Fallback to email username part if no username set
        return self.email.split('@')[0]
    
    @username.setter
    def username(self, value):
        """Set username in firebase data"""
        if not self.firebase_data:
            self.firebase_data = {}
        self.firebase_data['username'] = value
        # If we have UID, update in Firestore
        if hasattr(self, 'uid') and self.uid:
            try:
                db.collection('users').document(self.uid).update({'username': value})
            except Exception as e:
                current_app.logger.error(f"Error updating username: {e}")

    def get_id(self):
        return str(self.uid)
    
    def full_name(self):
        """Return full name"""
        if self.display_name:
            return self.display_name
        return self.email.split('@')[0]  # Fallback to email username part

def init_app(app):
    """Initialize Firebase with Flask app"""
    global firebase_app, db, time_offset
    
    # Check if Firebase is already initialized
    if firebase_app:
        return
    
    try:
        # Get the path to the service account key file
        service_account_path = app.config.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        
        # If it's a JSON string, write it to a temp file
        if isinstance(service_account_path, str) and service_account_path.startswith('{'):
            service_account_data = json.loads(service_account_path)
            service_account_path = 'temp_service_account.json'
            with open(service_account_path, 'w') as f:
                json.dump(service_account_data, f)
        
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': app.config.get('FIREBASE_STORAGE_BUCKET')
        })
        
        # Initialize Firestore
        db = firestore.client()
        
        # Get time offset from app config if available
        if hasattr(app, 'time_offset'):
            time_offset = app.time_offset
            app.logger.info(f'Using time offset of {time_offset} seconds for Firebase Authentication')
        
        app.logger.info('Firebase Authentication initialized successfully')
    except Exception as e:
        app.logger.error(f"Error initializing Firebase: {e}")
        raise

def get_user_document(uid):
    """Get a user document from Firestore by UID"""
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        current_app.logger.error(f"Firestore Error: {e}")
        return None

def get_user_by_email(email):
    """Get a user by email using Firebase Auth and Firestore"""
    try:
        # Get the Firebase Auth user
        firebase_user = auth.get_user_by_email(email)
        
        # Get the user data from Firestore
        user_data = get_user_document(firebase_user.uid)
        if not user_data:
            # Create a default user document if it doesn't exist
            user_data = {
                'email': firebase_user.email,
                'display_name': firebase_user.display_name,
                'phone_number': firebase_user.phone_number,
                'role': 'citizen',
                'department': None,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(firebase_user.uid).set(user_data)
        
        # Create a FirebaseUser object
        user = FirebaseUser(
            uid=firebase_user.uid,
            email=firebase_user.email,
            display_name=firebase_user.display_name or user_data.get('display_name'),
            phone_number=firebase_user.phone_number or user_data.get('phone_number'),
            role=user_data.get('role', 'citizen'),
            department=user_data.get('department'),
            firebase_data=user_data,
            is_active=not firebase_user.disabled
        )
        user.email_verified = firebase_user.email_verified
        
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return None

def get_user(uid):
    """Get a user by UID using Firebase Auth and Firestore"""
    try:
        # Get the Firebase Auth user
        firebase_user = auth.get_user(uid)
        
        # Get the user data from Firestore
        user_data = get_user_document(firebase_user.uid)
        if not user_data:
            # Create a default user document if it doesn't exist
            user_data = {
                'email': firebase_user.email,
                'display_name': firebase_user.display_name,
                'phone_number': firebase_user.phone_number,
                'role': 'citizen',
                'department': None,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(firebase_user.uid).set(user_data)
        
        # Create a FirebaseUser object
        user = FirebaseUser(
            uid=firebase_user.uid,
            email=firebase_user.email,
            display_name=firebase_user.display_name or user_data.get('display_name'),
            phone_number=firebase_user.phone_number or user_data.get('phone_number'),
            role=user_data.get('role', 'citizen'),
            department=user_data.get('department'),
            firebase_data=user_data,
            is_active=not firebase_user.disabled
        )
        user.email_verified = firebase_user.email_verified
        
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return None

def create_user(email, password, display_name=None, phone_number=None, role='citizen', department=None, username=None):
    """Create a new user in Firebase Auth and Firestore"""
    try:
        # Create the user in Firebase Auth
        user_properties = {
            'email': email,
            'password': password,
            'email_verified': False,
            'disabled': False,
        }
        
        if display_name:
            user_properties['display_name'] = display_name
            
        if phone_number and phone_number.startswith('+'):
            user_properties['phone_number'] = phone_number
            
        firebase_user = auth.create_user(**user_properties)
        
        # If no username is provided, use the email username part
        if not username:
            username = email.split('@')[0]
        
        # Create the user document in Firestore
        user_data = {
            'email': email,
            'display_name': display_name,
            'phone_number': phone_number,
            'role': role,
            'department': department,
            'username': username,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None,
            'is_online': False,
            'failed_login_attempts': 0,
            'last_failed_login': None
        }
        
        # Save the user data to Firestore
        db.collection('users').document(firebase_user.uid).set(user_data)
        
        # Create a FirebaseUser object
        user = FirebaseUser(
            uid=firebase_user.uid,
            email=email,
            display_name=display_name,
            phone_number=phone_number,
            role=role,
            department=department,
            firebase_data=user_data
        )
        
        return user
    except auth.EmailAlreadyExistsError:
        raise FirebaseAuthError("Email already exists")
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        raise FirebaseAuthError(str(e))

def authenticate_user(email, password):
    """Authenticate a user with Firebase Authentication REST API"""
    try:
        # This function simulates authentication using Firebase Admin SDK
        # In a real implementation, you would use the Firebase Auth REST API
        # Since we can't directly verify passwords with the Admin SDK
        
        # Check if the user exists
        try:
            user = auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            return None, "USER_NOT_FOUND"
        
        # Get the user data from Firestore
        user_ref = db.collection('users').document(user.uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            user_data = {
                'email': user.email,
                'display_name': user.display_name,
                'phone_number': user.phone_number,
                'role': 'citizen',
                'department': None,
                'created_at': firestore.SERVER_TIMESTAMP,
                'failed_login_attempts': 0,
                'last_failed_login': None
            }
        else:
            user_data = user_doc.to_dict()
            
        # Check if account is locked due to too many failed attempts
        max_attempts = current_app.config.get('MAX_FAILED_LOGIN_ATTEMPTS', 5)
        lockout_minutes = current_app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
        
        if (user_data.get('failed_login_attempts', 0) >= max_attempts and 
            user_data.get('last_failed_login') is not None):
            last_failed = user_data.get('last_failed_login')
            if isinstance(last_failed, firestore.SERVER_TIMESTAMP):
                # Handle server timestamp
                elapsed_minutes = 0  # Just created, not locked
            else:
                # Convert to datetime if needed
                if not isinstance(last_failed, datetime):
                    last_failed = last_failed.timestamp()
                    last_failed = datetime.fromtimestamp(last_failed)
                
                # Calculate elapsed minutes
                elapsed_minutes = (datetime.now() - last_failed).total_seconds() / 60
                
            if elapsed_minutes < lockout_minutes:
                # Account is locked
                return None, "ACCOUNT_LOCKED"
            else:
                # Reset failed attempts if lock duration has passed
                user_ref.update({
                    'failed_login_attempts': 0,
                    'last_failed_login': None
                })
        
        # In reality, we can't verify the password directly with the Admin SDK
        # This is a simulation - in production you would use the Firebase Auth REST API
        # For now, we're assuming the password is correct if we get to this point
        # and update the user data
        
        # Reset failed login attempts on successful login
        user_ref.update({
            'last_login': firestore.SERVER_TIMESTAMP,
            'is_online': True,
            'failed_login_attempts': 0,
            'last_failed_login': None
        })
        
        # Get updated user data
        user_data = user_ref.get().to_dict()
        
        # Create a FirebaseUser object
        firebase_user = FirebaseUser(
            uid=user.uid,
            email=user.email,
            display_name=user.display_name or user_data.get('display_name'),
            phone_number=user.phone_number or user_data.get('phone_number'),
            role=user_data.get('role', 'citizen'),
            department=user_data.get('department'),
            firebase_data=user_data,
            is_active=not user.disabled
        )
        firebase_user.email_verified = user.email_verified
        
        return firebase_user, None
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return None, str(e)

def update_user(uid, **kwargs):
    """Update a user in Firebase Auth and Firestore"""
    try:
        # Update the user in Firebase Auth
        auth_update = {}
        firestore_update = {}
        
        # Fields that can be updated in Firebase Auth
        auth_fields = ['display_name', 'email', 'phone_number', 'password', 'email_verified', 'disabled']
        
        for key, value in kwargs.items():
            if key in auth_fields:
                auth_update[key] = value
            firestore_update[key] = value
        
        # Update Firebase Auth if needed
        if auth_update:
            auth.update_user(uid, **auth_update)
        
        # Update Firestore
        if firestore_update:
            db.collection('users').document(uid).update(firestore_update)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        raise FirebaseAuthError(str(e))

def delete_user(uid):
    """Delete a user from Firebase Auth and Firestore"""
    try:
        # Delete the user from Firebase Auth
        auth.delete_user(uid)
        
        # Delete the user from Firestore
        db.collection('users').document(uid).delete()
        
        return True
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return False

def verify_id_token(id_token):
    """Verify a Firebase ID token and return the decoded token"""
    try:
        # Firebase only allows clock_skew_seconds between 0-60
        return auth.verify_id_token(
            id_token,
            check_revoked=False,
            clock_skew_seconds=60  # Maximum allowed value
        )
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return None

def generate_email_verification_link(email, action_code_settings=None):
    """Generate a verification link for the user"""
    try:
        # Create action code settings with redirect URL if not provided
        if action_code_settings is None:
            from flask import current_app
            base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
            action_code_settings = {
                'url': f"{base_url}/auth/verify_email_return",
                'handle_code_in_app': False,  # Process the code on the server
            }
        
        # Log the action code settings
        current_app.logger.info(f"Generating verification link with settings: {action_code_settings}")
        
        # Generate the email verification link
        verification_link = auth.generate_email_verification_link(
            email, 
            action_code_settings=auth.ActionCodeSettings(**action_code_settings)
        )
        
        return verification_link
    except Exception as e:
        current_app.logger.error(f"Error generating verification link: {str(e)}")
        return None

def generate_password_reset_link(email):
    """Generate a password reset link"""
    try:
        return auth.generate_password_reset_link(email)
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return None

def revoke_refresh_tokens(uid):
    """Revoke all refresh tokens for a user"""
    try:
        auth.revoke_refresh_tokens(uid)
        return True
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return False

def increment_failed_login(email):
    """Increment failed login attempts for a user"""
    try:
        user = auth.get_user_by_email(email)
        user_ref = db.collection('users').document(user.uid)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            failed_attempts = user_data.get('failed_login_attempts', 0) + 1
            user_ref.update({
                'failed_login_attempts': failed_attempts,
                'last_failed_login': firestore.SERVER_TIMESTAMP
            })
        else:
            user_ref.set({
                'email': user.email,
                'failed_login_attempts': 1,
                'last_failed_login': firestore.SERVER_TIMESTAMP
            }, merge=True)
        
        return True
    except auth.UserNotFoundError:
        return False
    except Exception as e:
        current_app.logger.error(f"Firebase Auth Error: {e}")
        return False

def create_audit_log(uid, action, resource_type, resource_id=None, details=None, ip_address=None):
    """Create an audit log entry in Firestore"""
    try:
        log_data = {
            'user_id': uid,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details,
            'ip_address': ip_address,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('audit_logs').add(log_data)
        return True
    except Exception as e:
        current_app.logger.error(f"Firestore Error: {e}")
        return False

def create_notification(uid, message, category=None, link=None):
    """Create a notification in Firestore"""
    try:
        notification_data = {
            'user_id': uid,
            'message': message,
            'category': category,
            'link': link,
            'is_read': False,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('notifications').add(notification_data)
        return True
    except Exception as e:
        current_app.logger.error(f"Firestore Error: {e}")
        return False

def authenticate_with_google_token(id_token):
    """Authenticate a user with a Google ID token"""
    try:
        current_app.logger.info("Authenticating with Google token...")
        
        # Verify the Google ID token with maximum allowed clock skew
        current_app.logger.info("Verifying ID token with Firebase...")
        decoded_token = auth.verify_id_token(
            id_token,
            check_revoked=False,
            clock_skew_seconds=60  # Maximum allowed value
        )
        uid = decoded_token['uid']
        current_app.logger.info(f"Token verified, user UID: {uid}")
        
        # Get the user from Firebase
        current_app.logger.info(f"Getting user details from Firebase Auth...")
        firebase_user = auth.get_user(uid)
        current_app.logger.info(f"Firebase user retrieved: {firebase_user.email}")
        
        # Get or create Firestore user document
        current_app.logger.info(f"Checking for user document in Firestore...")
        user_data = get_user_document(uid)
        if not user_data:
            current_app.logger.info(f"No user document found, creating one...")
            # Create a default user document if it doesn't exist
            user_data = {
                'email': firebase_user.email,
                'display_name': firebase_user.display_name,
                'phone_number': firebase_user.phone_number,
                'role': 'citizen',  # Default role for Google sign-ins
                'department': None,
                'created_at': firestore.SERVER_TIMESTAMP,
                'is_online': True
            }
            db.collection('users').document(uid).set(user_data)
            current_app.logger.info(f"User document created in Firestore")
        else:
            current_app.logger.info(f"User document found in Firestore")
        
        # Update last login and online status
        current_app.logger.info(f"Updating user login status...")
        db.collection('users').document(uid).update({
            'last_login': firestore.SERVER_TIMESTAMP,
            'is_online': True
        })
        
        # Create a FirebaseUser object
        current_app.logger.info(f"Creating FirebaseUser object...")
        user = FirebaseUser(
            uid=firebase_user.uid,
            email=firebase_user.email,
            display_name=firebase_user.display_name or user_data.get('display_name'),
            phone_number=firebase_user.phone_number or user_data.get('phone_number'),
            role=user_data.get('role', 'citizen'),
            department=user_data.get('department'),
            firebase_data=user_data,
            is_active=not firebase_user.disabled
        )
        user.email_verified = firebase_user.email_verified
        
        current_app.logger.info(f"Google authentication successful for {user.email}")
        return user
    except Exception as e:
        current_app.logger.error(f"Google Auth Error: {e}")
        # Log the full traceback for debugging
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def check_action_code(oob_code):
    """Check a Firebase action code (e.g., from email verification links)"""
    try:
        # Check the action code to verify it's valid
        action_info = auth.check_action_code(oob_code)
        # Return the email if verification is successful
        if action_info and action_info.data.get('email'):
            return action_info.data.get('email')
        return None
    except Exception as e:
        current_app.logger.error(f"Error checking action code: {str(e)}")
        return None

def apply_action_code(oob_code):
    """Apply a Firebase action code (e.g., complete email verification)"""
    try:
        # Apply the action code to complete the verification
        auth.confirm_email_verification(oob_code)
        return True
    except Exception as e:
        current_app.logger.error(f"Error applying action code: {str(e)}")
        return False 