from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime
from app import db
from app.models import User, AuditLog, Notification, OfficialRequest
from app.forms import EnhancedLoginForm, EnhancedRegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.utils.email import send_password_reset_email, send_email_verification
from app.utils.otp import generate_otp, store_otp, verify_otp_code, send_otp_email
from app import firebase_auth
import time
import ipaddress

auth = Blueprint('auth', __name__)

# Dictionary to track login attempts by IP
login_attempts = {}
# Max login attempts per hour per IP
MAX_LOGIN_ATTEMPTS_PER_IP = 10
# Time window in seconds (1 hour)
LOGIN_TIME_WINDOW = 3600

def check_rate_limit():
    """Check if the current IP has exceeded the rate limit"""
    ip = request.remote_addr
    current_time = time.time()
    
    # Initialize tracking for this IP if not exists
    if ip not in login_attempts:
        login_attempts[ip] = []
    
    # Remove attempts older than the time window
    login_attempts[ip] = [t for t in login_attempts[ip] if current_time - t < LOGIN_TIME_WINDOW]
    
    # Check if rate limit exceeded
    return len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS_PER_IP

def record_login_attempt():
    """Record a login attempt from the current IP"""
    ip = request.remote_addr
    current_time = time.time()
    
    if ip not in login_attempts:
        login_attempts[ip] = []
        
    login_attempts[ip].append(current_time)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    # Check rate limiting by IP
    if check_rate_limit():
        flash('Too many login attempts. Please try again later.', 'danger')
        return render_template('auth/login.html', form=EnhancedLoginForm(), rate_limited=True)
    
    form = EnhancedLoginForm()
    if form.validate_on_submit():
        # Record login attempt for rate limiting
        record_login_attempt()
        
        # Authenticate with Firebase Auth
        user, error = firebase_auth.authenticate_user(form.email.data, form.password.data)
        
        if error == "ACCOUNT_LOCKED":
            flash('Account temporarily locked due to too many failed login attempts. Please try again later or reset your password.', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user:
            # Increment failed attempts in Firebase
            firebase_auth.increment_failed_login(form.email.data)
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('This account has been deactivated. Please contact admin.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if email is verified (if email verification is required)
        if current_app.config.get('REQUIRE_EMAIL_VERIFICATION', False) and not user.email_verified:
            # Store email in session for verification
            session['verification_email'] = user.email
            
            # Generate and send OTP code
            otp_code = generate_otp()
            if store_otp(user.email, otp_code) and send_otp_email(user, otp_code):
                flash('Please verify your email address. We have sent a verification code to your email.', 'warning')
            else:
                flash('Unable to send verification code. Please try again or contact support.', 'danger')
                
            # Redirect to OTP verification page
            return redirect(url_for('auth.verify_otp', email=user.email))
        
        # Create login audit log
        firebase_auth.create_audit_log(
            uid=user.uid,
            action='login',
            resource_type='user',
            resource_id=user.uid,
            details='User logged in',
            ip_address=request.remote_addr
        )
        
        # Remember user login
        login_user(user, remember=form.remember_me.data)
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('citizen.dashboard')
        
        # Redirect based on role
        if user.role == 'admin':
            next_page = url_for('admin.dashboard')
        elif user.role == 'official' and form.department.data:
            session['department'] = form.department.data
            next_page = url_for('admin.dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        # Create logout audit log for Firebase users
        if hasattr(current_user, 'uid'):
            # Firebase user
            firebase_auth.create_audit_log(
                uid=current_user.uid,
                action='logout',
                resource_type='user',
                resource_id=current_user.uid,
                details='User logged out',
                ip_address=request.remote_addr
        )
            
            # Update user status
            firebase_auth.update_user(
                current_user.uid,
                is_online=False
            )
        else:
            # SQLite user - handled by event listener in __init__.py
            pass
    
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = EnhancedRegistrationForm()
    if form.validate_on_submit():
        try:
            # Create display name from first and last name
            display_name = f"{form.first_name.data} {form.last_name.data}"
            
            # Create the user in Firebase Auth and Firestore
            user = firebase_auth.create_user(
                email=form.email.data,
                password=form.password.data,
                display_name=display_name,
                phone_number=form.phone.data if form.phone.data and form.phone.data.startswith('+') else None,
                role='citizen',  # Always start as citizen for security
                username=form.username.data  # Pass username directly to create_user
            )
            
            # Additional user data to store in Firestore
            firebase_auth.update_user(
                user.uid,
                address=form.address.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
                    
            # Create registration audit log
            firebase_auth.create_audit_log(
                uid=user.uid,
                action='register',
                resource_type='user',
                resource_id=user.uid,
                details='New user registered',
                ip_address=request.remote_addr
            )
            
            # If user requested official role, create pending request
            if form.role.data == 'official':
                # Store official request data in Firestore
                official_request = {
                    'user_id': user.uid,
                    'department': form.department.data,
                    'position': form.position.data,
                    'employee_id': form.employee_id.data,
                    'office_phone': form.office_phone.data,
                    'justification': form.justification.data,
                    'status': 'pending',
                    'created_at': datetime.utcnow()
                }
                
                # Add official request to Firestore
                firebase_auth.db.collection('official_requests').add(official_request)
                
                # Create notification for admin
                firebase_auth.create_notification(
                    uid=None,  # For all admins
                    message=f"New official account request from {display_name}",
                    category='official_request',
                    link=url_for('admin.official_requests')
                )
            
            # Send OTP verification if required
            if current_app.config.get('REQUIRE_EMAIL_VERIFICATION', False):
                try:
                    # Generate OTP
                    otp_code = generate_otp()
                    current_app.logger.info(f"Generated OTP for new user {user.email}")
                    
                    # Store the OTP code in the session for fallback display in development
                    if current_app.debug:
                        session['debug_otp'] = otp_code
                    
                    if store_otp(user.email, otp_code) and send_otp_email(user, otp_code):
                        current_app.logger.info(f"OTP sent to new user {user.email}")
                        # Store email in session for verification
                        session['verification_email'] = user.email
                        flash('Registration successful! Please verify your email with the verification code we sent.', 'success')
                        return redirect(url_for('auth.verify_otp', email=user.email))
                    else:
                        current_app.logger.error(f"Failed to send OTP to new user {user.email}")
                        flash('Registration successful! Please login and request a new verification code.', 'warning')
                except Exception as e:
                    current_app.logger.error(f"Error sending OTP: {e}")
                    flash('Registration successful! Please login to your account.', 'success')
            else:
                flash('Registration successful! Please login to your account.', 'success')
            
            return redirect(url_for('auth.login'))
            
        except firebase_auth.FirebaseAuthError as e:
            flash(f'Error creating account: {str(e)}', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Handle OTP verification"""
    # Get email from query parameter or form data
    email = request.args.get('email') or request.form.get('email') or session.get('verification_email')
    
    if not email:
        flash('Email address is required for verification.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Store in session
    session['verification_email'] = email
    
    # Get any debug OTP from session (for fallback display)
    debug_otp = session.get('debug_otp')
    show_debug = current_app.debug and debug_otp
    
    if request.method == 'POST':
        # Process OTP verification
        otp_code = request.form.get('otp_code')
        
        if not otp_code:
            return render_template('auth/verify_otp.html', 
                                  email=email, 
                                  verification_error='Please enter the verification code.')
        
        # Verify OTP - using the imported function with alias
        if verify_otp_code(email, otp_code):
            # Clear session data
            session.pop('verification_email', None)
            session.pop('debug_otp', None)
            
            # Success message
            flash('Email verification successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Failed verification
            return render_template('auth/verify_otp.html', 
                                  email=email, 
                                  verification_error='Invalid or expired verification code. Please try again or request a new code.')
    
    # GET request - show verification form
    return render_template('auth/verify_otp.html', email=email, 
                          debug_otp=debug_otp if show_debug else None)

@auth.route('/resend_otp', methods=['POST'])
def resend_otp():
    """Resend OTP verification code"""
    email = request.form.get('email') or session.get('verification_email')
    
    if not email:
        flash('Email address is required.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Get the user from Firebase
        user = firebase_auth.get_user_by_email(email)
        if not user:
            # Don't reveal that the user doesn't exist
            flash('Verification code sent. Please check your inbox.', 'info')
            return redirect(url_for('auth.verify_otp', email=email))
        
        # Don't send if already verified
        if user.email_verified:
            flash('Your email is already verified. You can now log in.', 'info')
            return redirect(url_for('auth.login'))
        
        # Generate new OTP
        otp_code = generate_otp()
        current_app.logger.info(f"Generated new OTP for {email}")
        
        # Store the OTP code in the session for fallback display in development
        if current_app.debug:
            session['debug_otp'] = otp_code
            current_app.logger.info(f"Debug OTP stored in session: {otp_code}")
        
        # Store in Firestore even if email fails
        store_success = store_otp(email, otp_code)
        if not store_success:
            current_app.logger.error(f"Failed to store OTP for {email}")
            flash('An error occurred. Please try again later.', 'danger')
            return redirect(url_for('auth.verify_otp', email=email))
        
        # Try to send email
        if send_otp_email(user, otp_code):
            current_app.logger.info(f"New OTP sent successfully to {email}")
            
            # Log the action
            firebase_auth.create_audit_log(
                uid=user.uid,
                action='resend_otp',
                resource_type='user',
                resource_id=user.uid,
                details='Verification code resent',
                ip_address=request.remote_addr
            )
            
            # Success message
            flash('Verification code sent. Please check your inbox.', 'info')
        else:
            # Even if email fails, we can still use the OTP from debug session in development
            current_app.logger.error(f"Failed to send new OTP to {email}")
            if current_app.debug:
                flash('Email sending failed, but the code is displayed below for development.', 'warning')
            else:
                flash('There was a problem sending the verification code. Please try again later.', 'warning')
    except Exception as e:
        current_app.logger.error(f"Error resending OTP: {e}")
        # Don't reveal errors
        flash('Verification code sent. Please check your inbox.', 'info')
    
    return redirect(url_for('auth.verify_otp', email=email))

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        try:
            # Generate Firebase password reset link
            reset_link = firebase_auth.generate_password_reset_link(form.email.data)
            
            if reset_link:
                # Get user data to send email
                user = firebase_auth.get_user_by_email(form.email.data)
                if user:
                    # Send password reset email
                    send_password_reset_email(user, reset_link)
            
                    # Log password reset request
                    firebase_auth.create_audit_log(
                        uid=user.uid,
                        action='password_reset_request',
                        resource_type='user',
                        resource_id=user.uid,
                        details='Password reset requested',
                        ip_address=request.remote_addr
                    )
            
            # Always show success message even if user doesn't exist (security)
            flash('Check your email for instructions to reset your password', 'info')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Error requesting password reset: {e}")
            # Don't reveal error details to user
        flash('Check your email for instructions to reset your password', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@auth.route('/reset_password/<token>')
def reset_password(token):
    # Firebase handles password reset directly through their own URLs
    # This route is just a placeholder or for redirection if needed
    flash('Please follow the password reset instructions from the email.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/request_official_account', methods=['GET', 'POST'])
@login_required
def request_official_account():
    """Handle requests to become a government official"""
    # Only citizens can request official accounts
    if current_user.role != 'citizen':
        flash('You already have elevated access privileges.', 'info')
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('official.dashboard'))
    
    from app.forms import OfficialRequestForm
    from app.models import OfficialRequest
    
    form = OfficialRequestForm()
    success = False
    
    if form.validate_on_submit():
        # Check if user already has a pending request
        existing_request = OfficialRequest.query.filter_by(
            user_id=current_user.id, 
            status='pending'
        ).first()
        
        if existing_request:
            flash('You already have a pending request. Please wait for administrators to review it.', 'warning')
            return redirect(url_for('citizen.dashboard'))
        
        # Handle custom department if "Other" is selected
        department = form.department.data
        if department == 'Other':
            other_department = request.form.get('other_department')
            if other_department and other_department.strip():
                department = other_department.strip()
            else:
                flash('Please specify the custom department name.', 'danger')
                return render_template('auth/request_official_account.html', title='Request Official Account', form=form, success=False)
        
        # Create new request
        official_request = OfficialRequest(
            user_id=current_user.id,
            department=department,
            position=form.position.data,
            employee_id=form.employee_id.data,
            office_phone=form.office_phone.data,
            justification=form.justification.data
        )
        db.session.add(official_request)
        
        # Create audit log
        log = AuditLog(
            user_id=current_user.id,
            action='request_official_account',
            resource_type='official_request',
            resource_id=official_request.id,
            details=f'User requested official account for department: {department}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Notify administrators (in a real app, would send emails)
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                title='New Official Account Request',
                message=f'User {current_user.full_name()} has requested an official account for the {department} department.'
            )
            db.session.add(notification)
        db.session.commit()
        
        success = True
        flash('Your request for an official account has been submitted successfully.', 'success')
    
    return render_template('auth/request_official_account.html', 
                           title='Request Official Account',
                           form=form,
                           success=success) 

@auth.route('/resend_verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    email = request.form.get('email')
    
    if not email:
        flash('Email address is required.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Get the user from Firebase
        user = firebase_auth.get_user_by_email(email)
        if not user:
            # Don't reveal that the user doesn't exist
            flash('Verification email sent. Please check your inbox.', 'info')
            return redirect(url_for('auth.login'))
        
        # Don't send if already verified
        if user.email_verified:
            flash('Your email is already verified. You can now log in.', 'info')
            return redirect(url_for('auth.login'))
        
        # Generate verification link
        current_app.logger.info(f"Generating verification link for {email}")
        verification_link = firebase_auth.generate_email_verification_link(email)
        
        if verification_link:
            # Send verification email
            current_app.logger.info(f"Sending verification email to {email}")
            email_sent = send_email_verification(user, verification_link)
            
            if email_sent:
                # Log the action
                current_app.logger.info(f"Verification email successfully sent to {email}")
                firebase_auth.create_audit_log(
                    uid=user.uid,
                    action='resend_verification',
                    resource_type='user',
                    resource_id=user.uid,
                    details='Verification email resent',
                    ip_address=request.remote_addr
                )
                
                flash('Verification email sent. Please check your inbox.', 'info')
            else:
                current_app.logger.error(f"Failed to send verification email to {email}")
                flash('There was a problem sending the verification email. Please try again later.', 'warning')
        else:
            current_app.logger.error(f"Could not generate verification link for {email}")
            flash('Could not generate verification link. Please try again later.', 'warning')
    except Exception as e:
        current_app.logger.error(f"Error resending verification email: {e}")
        flash('Verification email sent. Please check your inbox.', 'info')
    
    return redirect(url_for('auth.login'))

@auth.route('/google_signin', methods=['POST'])
def google_signin():
    """Handle Google Sign-In"""
    # Get the ID token from the request
    try:
        data = request.get_json()
        if not data:
            current_app.logger.error("Google sign-in: No JSON data in request")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        id_token = data.get('idToken')
        
        if not id_token:
            current_app.logger.error("Google sign-in: No ID token provided")
            return jsonify({'success': False, 'error': 'No ID token provided'}), 400
        
        current_app.logger.info(f"Google sign-in: Processing token (length: {len(id_token)})")
        
        # Authenticate with Google token
        user = firebase_auth.authenticate_with_google_token(id_token)
        
        if not user:
            current_app.logger.error("Google sign-in: Authentication failed - no user returned")
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        
        current_app.logger.info(f"Google sign-in: User authenticated - {user.email}")
        
        # Create login audit log
        firebase_auth.create_audit_log(
            uid=user.uid,
            action='login_google',
            resource_type='user',
            resource_id=user.uid,
            details='User logged in with Google',
            ip_address=request.remote_addr
        )
        
        # Remember user login
        login_user(user)
        current_app.logger.info(f"Google sign-in: User logged in with Flask-Login")
        
        # Determine redirect URL based on role
        if user.role == 'admin':
            redirect_url = url_for('admin.dashboard')
        elif user.role == 'official':
            redirect_url = url_for('admin.dashboard')
        else:
            redirect_url = url_for('citizen.dashboard')
        
        current_app.logger.info(f"Google sign-in: Redirecting to {redirect_url}")
        return jsonify({'success': True, 'redirect': redirect_url})
    
    except Exception as e:
        error_message = str(e)
        current_app.logger.error(f"Google sign-in error: {error_message}")
        return jsonify({'success': False, 'error': f'Authentication error: {error_message}'}), 500 
