"""
Trekk Management App — Trek Staff Dashboard Routes

Trek Staff routes for managing assigned treks.
Full functionality will be implemented in Milestone 4.
"""

from flask import Blueprint, render_template
from flask_login import current_user
from app.utils.decorators import staff_required
from app.models.trek_assignment import TrekAssignment

staff_bp = Blueprint('staff_bp', __name__, url_prefix='/staff')


@staff_bp.route('/dashboard')
@staff_required
def dashboard():
    """Staff dashboard — overview of assigned treks."""
    # Get assigned treks for current staff member
    assignments = TrekAssignment.query.filter_by(
        staff_id=current_user.id,
        is_active=True
    ).all()

    stats = {
        'assigned_treks': len(assignments),
    }

    return render_template('staff/dashboard.html', stats=stats, assignments=assignments)
