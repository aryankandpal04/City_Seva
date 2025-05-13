from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime
from app import db
from app.models import User, AuditLog, Notification, OfficialRequest
from app.forms import EnhancedLoginForm, EnhancedRegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.utils.email import send_password_reset_email, send_email_verification
from app.utils.otp import generate_otp, store_otp, verify_otp_code, send_otp_email, OTP
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

def create_audit_log(user_id, action, resource_type, resource_id=None, details=None, ip_address=None):
    """Create an audit log entry in SQLite"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()
    return log

def create_notification(user_id, title, message, is_read=False):
    """Create a notification in SQLite"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=is_read
    )
    db.session.add(notification)
    db.session.commit()
    return notification

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
        
        # Authenticate with SQLite database
        user = User.query.filter_by(email=form.email.data).first()
        
        # If no user found or password is incorrect
        if user is None or not user.verify_password(form.password.data):
            # If user exists, increment failed login attempts
            if user:
                # Add logic for account locking after too many failed attempts
                # Example: if user.failed_login_attempts > MAX_ATTEMPTS: lock account
                flash('Invalid email or password', 'danger')
            else:
                flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('This account has been deactivated. Please contact admin.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user has a pending official request
        pending_request = OfficialRequest.query.filter_by(
            user_id=user.id,
            status='pending'
        ).first()
        
        if pending_request and (form.role.data == 'official' or user.role == 'citizen'):
            flash('Your government official account request is pending approval. You will be notified once approved.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if email is verified (if email verification is required)
        if current_app.config.get('REQUIRE_EMAIL_VERIFICATION', False):
            # Since the email_verified column might not exist, we'll check if there's an OTP record
            otp = OTP.query.filter_by(email=user.email).first()
            if otp:
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
        create_audit_log(
            user_id=user.id,
            action='login',
            resource_type='user',
            resource_id=user.id,
            details='User logged in',
            ip_address=request.remote_addr
        )
        
        # Update last login time
        user.last_login = datetime.utcnow()
        user.is_online = True
        db.session.commit()
        
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
        # Create logout audit log
        create_audit_log(
            user_id=current_user.id,
            action='logout',
            resource_type='user',
            resource_id=current_user.id,
            details='User logged out',
            ip_address=request.remote_addr
        )
        
        # User status update is handled by event listener in __init__.py
    
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = EnhancedRegistrationForm()
    if form.validate_on_submit():
        try:
            # Create new user in SQLite
            user = User(
                email=form.email.data,
                username=form.username.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                address=form.address.data,
                role='citizen',  # Always start as citizen for security
                created_at=datetime.utcnow()
            )
            user.password = form.password.data  # This uses the property setter to hash the password
            
            # Add user to database
            db.session.add(user)
            db.session.commit()
            
            # Create registration audit log
            create_audit_log(
                user_id=user.id,
                action='register',
                resource_type='user',
                resource_id=user.id,
                details='New user registered',
                ip_address=request.remote_addr
            )
            
            # If user requested official role, create pending request
            if form.role.data == 'official':
                # Store the requested role in session to check during OTP verification
                session['requested_role'] = 'official'
                
                # Create official request in SQLite
                official_request = OfficialRequest(
                    user_id=user.id,
                    department=form.department.data,
                    position=form.position.data,
                    employee_id=form.employee_id.data,
                    office_phone=form.office_phone.data,
                    justification=form.justification.data,
                    status='pending',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(official_request)
                db.session.commit()
                
                # Create notification for all admins
                admin_users = User.query.filter_by(role='admin').all()
                for admin in admin_users:
                    create_notification(
                        user_id=admin.id,
                        title="New Official Request",
                        message=f"New official account request from {user.full_name()}"
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
                    
                    # Store OTP in the database (indicates email is not yet verified)
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
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Handle OTP verification"""
    email = request.args.get('email') or session.get('verification_email') or request.form.get('email')
    
    if not email:
        flash('Email not provided for verification.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # Get OTP code from form - check both field names for backward compatibility
        otp_code = request.form.get('otp_code') or request.form.get('otp')
        
        if not otp_code:
            flash('Please enter the verification code.', 'warning')
            return render_template('auth/verify_otp.html', email=email)
        
        current_app.logger.info(f"Attempting to verify OTP for {email} with code {otp_code}")
        
        # Verify OTP
        if verify_otp_code(email, otp_code):
            current_app.logger.info(f"OTP verification successful for {email}")
            
            # Find user
            user = User.query.filter_by(email=email).first()
            
            if user:
                current_app.logger.info(f"User found for verified email {email}")
                
                # Check if this was a government official registration
                official_request = OfficialRequest.query.filter_by(
                    user_id=user.id, 
                    status='pending'
                ).first()
                
                if official_request or (session.get('requested_role') == 'official'):
                    # For government officials, don't login after OTP verification
                    # They need admin approval first
                    flash('Your email has been verified successfully! Your account is pending approval by the administrator. You will be notified once your account is approved.', 'success')
                    # Clear the requested_role from session
                    if 'requested_role' in session:
                        session.pop('requested_role')
                    return redirect(url_for('auth.login'))
                
                # For regular citizens or already approved officials, proceed with login
                if not current_user.is_authenticated:
                    # Log the user in
                    login_user(user)
                    
                    # Create login audit log
                    create_audit_log(
                        user_id=user.id,
                        action='login_after_verification',
                        resource_type='user',
                        resource_id=user.id,
                        details='User logged in after email verification',
                        ip_address=request.remote_addr
                    )
                    
                    # Update last login time
                    user.last_login = datetime.utcnow()
                    user.is_online = True
                    db.session.commit()
                    
                    flash('Email verified successfully! You have been logged in.', 'success')
                else:
                    flash('Email verified successfully!', 'success')
                
                # Redirect based on role
                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.role == 'official':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('citizen.dashboard'))
            else:
                current_app.logger.error(f"No user found for verified email {email}")
                flash('User not found. Please register again.', 'danger')
                return redirect(url_for('auth.register'))
        else:
            current_app.logger.warning(f"OTP verification failed for {email}")
            flash('Invalid or expired verification code. Please try again.', 'danger')
    
    # Display fallback OTP in development mode
    debug_otp = session.get('debug_otp') if current_app.debug else None
    
    return render_template('auth/verify_otp.html', email=email, debug_otp=debug_otp)

@auth.route('/resend_otp', methods=['POST'])
def resend_otp():
    """Resend OTP verification code"""
    email = request.form.get('email') or session.get('verification_email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email not provided.'}), 400
    
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    
    # Generate new OTP
    otp_code = generate_otp()
    
    # Store in session for debug in development
    if current_app.debug:
        session['debug_otp'] = otp_code
    
    # Store and send OTP
    if store_otp(email, otp_code) and send_otp_email(user, otp_code):
        return jsonify({
            'success': True, 
            'message': 'Verification code resent successfully.',
            'debug_otp': otp_code if current_app.debug else None
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to send verification code.'}), 500

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Handle password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            send_password_reset_email(user)
            flash('Check your email for instructions to reset your password', 'info')
        else:
            # Don't reveal if email exists in database
            flash('If that email address is registered, we have sent instructions to reset your password', 'info')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    # Verify token and get user
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # Set new password
        user.password = form.password.data
        db.session.commit()
        
        # Create audit log
        create_audit_log(
            user_id=user.id,
            action='reset_password',
            resource_type='user',
            resource_id=user.id,
            details='Password reset successfully',
            ip_address=request.remote_addr
        )
        
        flash('Your password has been reset successfully', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', form=form)

@auth.route('/request_official_account', methods=['GET', 'POST'])
@login_required
def request_official_account():
    """Handle request for official account privileges"""
    # Check if user already has an official request pending
    existing_request = OfficialRequest.query.filter_by(
        user_id=current_user.id, 
        status='pending'
    ).first()
    
    if existing_request:
        flash('You already have a pending request for an official account.', 'warning')
        return redirect(url_for('citizen.dashboard'))
    
    # Check if user is already an official
    if current_user.role == 'official':
        flash('You already have an official account.', 'info')
        return redirect(url_for('citizen.dashboard'))
    
    form = EnhancedRegistrationForm(is_official_request=True)
    
    # Pre-fill form with user data
    form.email.data = current_user.email
    form.email.render_kw = {'readonly': True}
    form.username.data = current_user.username
    form.username.render_kw = {'readonly': True}
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    form.phone.data = current_user.phone
    form.address.data = current_user.address
    
    if form.validate_on_submit():
        # Create new official request
        official_request = OfficialRequest(
            user_id=current_user.id,
            department=form.department.data,
            position=form.position.data,
            employee_id=form.employee_id.data,
            office_phone=form.office_phone.data,
            justification=form.justification.data,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.session.add(official_request)
        db.session.commit()
        
        # Notify all admin users
        admin_users = User.query.filter_by(role='admin').all()
        for admin in admin_users:
            create_notification(
                user_id=admin.id,
                title="New Official Request",
                message=f"New official account request from {current_user.full_name()}"
            )
        
        flash('Your request for an official account has been submitted and is pending approval.', 'success')
        return redirect(url_for('citizen.dashboard'))
    
    return render_template('auth/request_official.html', title='Request Official Account', form=form) 
