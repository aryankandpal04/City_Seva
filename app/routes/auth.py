from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime
from app import db
from app.models import User, AuditLog, Notification, OfficialRequest
from app.forms import EnhancedLoginForm, EnhancedRegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.utils.email import send_password_reset_email

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = EnhancedLoginForm()
    if form.validate_on_submit():
        # Find the user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.verify_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('This account has been deactivated. Please contact admin.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check for role and department requirements
        if form.role.data == 'official':
            # If trying to login as official but is a citizen
            if user.role == 'citizen':
                # Check if they have a pending request
                pending_request = OfficialRequest.query.filter_by(
                    user_id=user.id, 
                    status='pending'
                ).first()
                
                if pending_request:
                    flash('Your official account request is still pending approval. You can log in as a citizen for now.', 'warning')
                else:
                    flash('You do not have official account privileges. Please register for an official account first.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Ensure we're treating the user as an official and set the department
            if user.role == 'official' and user.department != form.department.data:
                flash(f'You are not registered with the {dict(form.department.choices).get(form.department.data)} department.', 'danger')
                return redirect(url_for('auth.login'))
        
        # If trying to log in as citizen but is an official, that's fine
        
        login_user(user, remember=form.remember_me.data)
        
        # Update last login time
        user.last_login = datetime.utcnow()
        
        # Save the login role for this session
        login_role = 'Government Official' if form.role.data == 'official' and user.role == 'official' else 'Citizen'
        
        # Log login action with the proper role title
        log = AuditLog(
            user_id=user.id,
            action='login',
            resource_type='user',
            resource_id=user.id,
            details=f'User logged in as {login_role}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Redirect to next page or dashboard based on role
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if user.role == 'admin':
                next_page = url_for('admin.dashboard')
            elif user.role == 'official':
                next_page = url_for('admin.dashboard')
            else:
                next_page = url_for('citizen.dashboard')
        
        flash(f'Welcome! You are logged in as a {login_role}.', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        # Log logout action
        log = AuditLog(
            user_id=current_user.id,
            action='logout',
            resource_type='user',
            resource_id=current_user.id,
            details='User logged out',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = EnhancedRegistrationForm()
    if form.validate_on_submit():
        # Create user with common fields
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            role='citizen'  # Always start as citizen for security
        )
        user.password = form.password.data
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration action
        log = AuditLog(
            user_id=user.id,
            action='register',
            resource_type='user',
            resource_id=user.id,
            details='New user registered',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        # If the user selected to register as an official, create an official request
        if form.role.data == 'official':
            # Create verification request for the official account
            official_request = OfficialRequest(
                user_id=user.id,
                department=form.department.data,
                position=form.position.data,
                employee_id=form.employee_id.data,
                office_phone=form.office_phone.data,
                justification=form.justification.data,
                status='pending'
            )
            db.session.add(official_request)
            
            # Log official request
            log = AuditLog(
                user_id=user.id,
                action='request_official_account',
                resource_type='official_request',
                resource_id=official_request.id,
                details=f'User requested official account during registration for department: {form.department.data}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            
            # Notify administrators
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                notification = Notification(
                    user_id=admin.id,
                    title='New Official Account Request',
                    message=f'New user {user.full_name()} has registered and requested an official account for the {form.department.data} department.'
                )
                db.session.add(notification)
            
            flash('Registration successful! Your account has been created and your official account request has been submitted for verification. You can log in as a citizen while your request is being processed.', 'success')
        else:
            flash('Registration successful! You can now log in.', 'success')
            
        db.session.commit()
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            
            # Log password reset request
            log = AuditLog(
                user_id=user.id,
                action='password_reset_request',
                resource_type='user',
                resource_id=user.id,
                details='Password reset requested',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
        
        flash('Check your email for instructions to reset your password', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('citizen.dashboard'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()
        
        # Log password reset action
        log = AuditLog(
            user_id=user.id,
            action='password_reset',
            resource_type='user',
            resource_id=user.id,
            details='Password reset completed',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Your password has been reset', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Reset Password', form=form)

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
        
        # Create new request
        official_request = OfficialRequest(
            user_id=current_user.id,
            department=form.department.data,
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
            details=f'User requested official account for department: {form.department.data}',
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
                message=f'User {current_user.full_name()} has requested an official account for the {form.department.data} department.'
            )
            db.session.add(notification)
        db.session.commit()
        
        success = True
        flash('Your request for an official account has been submitted successfully.', 'success')
    
    return render_template('auth/request_official_account.html', 
                           title='Request Official Account',
                           form=form,
                           success=success) 