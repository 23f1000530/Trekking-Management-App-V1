"""
Trekk Management App — Trekker Dashboard Routes

Trekker routes for browsing and booking treks.
Full functionality will be implemented in later milestones.
"""

from flask import Blueprint, render_template
from flask_login import current_user
from app.utils.decorators import trekker_required
from app.models.booking import Booking

trekker_bp = Blueprint('trekker_bp', __name__, url_prefix='/trekker')


@trekker_bp.route('/dashboard')
@trekker_required
def dashboard():
    """Trekker dashboard — overview of bookings."""
    # Get current user's bookings
    my_bookings = Booking.query.filter_by(user_id=current_user.id).all()

    stats = {
        'total_bookings': len(my_bookings),
        'active_bookings': len([b for b in my_bookings if b.booking_status in ('pending', 'confirmed')]),
    }

    return render_template('trekker/dashboard.html', stats=stats, bookings=my_bookings)
