"""
Trekk Management App — Authentication Routes

Handles user registration (Trekker & Staff), login, and logout.
Admin is pre-created and cannot register.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.staff_profile import StaffProfile

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login for all roles."""
    # If already logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validate input
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')

        # Find user
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html')

        # Check if user is active (not blacklisted/deactivated)
        if not user.is_active:
            flash('Your account has been deactivated. Please contact the administrator.', 'error')
            return render_template('auth/login.html')

        # Check if trek staff is approved
        if user.is_trek_staff and not user.is_approved:
            flash('Your staff account is pending admin approval. Please wait for approval before logging in.', 'warning')
            return render_template('auth/login.html')

        # Login successful
        login_user(user)
        flash(f'Welcome back, {user.username}!', 'success')

        # Redirect to the page they were trying to access, or their dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect_to_dashboard(user)

    return render_template('auth/login.html')


@auth.route('/register/trekker', methods=['GET', 'POST'])
def register_trekker():
    """Handle trekker (regular user) registration."""
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        errors = validate_registration(username, email, password, confirm_password)
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register_trekker.html')

        # Create trekker user
        user = User(
            username=username,
            email=email,
            role='trekker',
            is_active=True,
            is_approved=True,  # Trekkers are auto-approved
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Auto-login after registration
        login_user(user)
        flash('Registration successful! Welcome to Trekk Management.', 'success')
        return redirect(url_for('trekker_bp.dashboard'))

    return render_template('auth/register_trekker.html')


@auth.route('/register/staff', methods=['GET', 'POST'])
def register_staff():
    """Handle trek staff registration (requires admin approval)."""
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        experience_years = request.form.get('experience_years', '0')
        specialization = request.form.get('specialization', '').strip()

        # Validation
        errors = validate_registration(username, email, password, confirm_password)
        if not full_name:
            errors.append('Full name is required.')
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register_staff.html')

        # Parse experience years
        try:
            exp_years = int(experience_years) if experience_years else 0
        except ValueError:
            exp_years = 0

        # Create staff user (NOT approved — requires admin approval)
        user = User(
            username=username,
            email=email,
            role='trek_staff',
            is_active=True,
            is_approved=False,  # Requires admin approval
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()  # Get user.id before creating profile

        # Create staff profile
        profile = StaffProfile(
            user_id=user.id,
            full_name=full_name,
            phone=phone if phone else None,
            experience_years=exp_years,
            specialization=specialization if specialization else None,
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration submitted! Your account is pending admin approval. '
              'You will be able to log in once an admin approves your account.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_staff.html')


@auth.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ── Helper Functions ───────────────────────────────────────────────────

def redirect_to_dashboard(user):
    """Redirect user to their role-specific dashboard."""
    if user.is_admin:
        return redirect(url_for('admin_bp.dashboard'))
    elif user.is_trek_staff:
        return redirect(url_for('staff_bp.dashboard'))
    else:
        return redirect(url_for('trekker_bp.dashboard'))


def validate_registration(username, email, password, confirm_password):
    """Validate registration form data. Returns a list of error messages."""
    errors = []

    if not username or len(username) < 3:
        errors.append('Username must be at least 3 characters long.')

    if not email or '@' not in email:
        errors.append('Please enter a valid email address.')

    if not password or len(password) < 6:
        errors.append('Password must be at least 6 characters long.')

    if password != confirm_password:
        errors.append('Passwords do not match.')

    # Check if username or email already exists
    if username and User.query.filter_by(username=username).first():
        errors.append('Username is already taken.')

    if email and User.query.filter_by(email=email).first():
        errors.append('Email is already registered.')

    return errors
