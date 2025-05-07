from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('citizen.index'))
        return f(*args, **kwargs)
    return decorated_function

def official_required(f):
    """Decorator to restrict access to official users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'official']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('citizen.index'))
        return f(*args, **kwargs)
    return decorated_function 