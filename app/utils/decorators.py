"""
Trekk Management App — Role-Based Access Decorators

Provides decorators to restrict route access based on user roles.
Used in conjunction with Flask-Login's @login_required.
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required


def role_required(role):
    """
    Generic decorator that restricts access to users with a specific role.
    Must be used AFTER @login_required.

    Usage:
        @app.route('/admin')
        @login_required
        @role_required('admin')
        def admin_page():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Restrict access to admin users only."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    """Restrict access to approved trek staff only."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'trek_staff':
            abort(403)
        if not current_user.is_approved:
            flash('Your account is pending admin approval. Please wait.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def trekker_required(f):
    """Restrict access to trekker users only."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'trekker':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
