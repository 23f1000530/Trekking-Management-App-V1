"""
Trekk Management App — Admin Dashboard Routes

Admin-only routes for system management.
Full functionality will be implemented in Milestone 3.
"""

from flask import Blueprint, render_template
from flask_login import current_user
from app.utils.decorators import admin_required
from app import db
from app.models.user import User
from app.models.trek import Trek
from app.models.booking import Booking

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard — overview of system stats."""
    # Gather stats for the dashboard
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = User.query.filter_by(role='trek_staff').count()
    pending_staff = User.query.filter_by(role='trek_staff', is_approved=False).count()
    total_bookings = Booking.query.count()

    stats = {
        'total_treks': total_treks,
        'total_users': total_users,
        'total_staff': total_staff,
        'pending_staff': pending_staff,
        'total_bookings': total_bookings,
    }

    return render_template('admin/dashboard.html', stats=stats)
