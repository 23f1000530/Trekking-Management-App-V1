"""
Trekk Management App — Trek Staff Dashboard Routes

Trek Staff routes for managing assigned treks:
- Dashboard with assigned treks and registered trekkers count
- Profile update
- Trek detail with participant management
- Update available trek slots
- Update trek status (Open/Closed/Started/Ongoing/Completed)
- View registered users for each trek
- Access control: Only assigned staff can manage their treks
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.utils.decorators import staff_required
from app import db
from app.models.user import User
from app.models.trek import Trek
from app.models.booking import Booking
from app.models.staff_profile import StaffProfile
from app.models.trek_assignment import TrekAssignment

staff_bp = Blueprint('staff_bp', __name__, url_prefix='/staff')


def _get_assigned_trek_or_403(trek_id):
    """Helper to verify the current staff member is assigned to the trek."""
    trek = Trek.query.get_or_404(trek_id)
    assignment = TrekAssignment.query.filter_by(
        staff_id=current_user.id,
        trek_id=trek_id,
        is_active=True,
    ).first()

    if not assignment:
        flash('You are not assigned to this trek.', 'error')
        return None, None

    return trek, assignment


# ── Dashboard ──────────────────────────────────────────────────────────
@staff_bp.route('/dashboard')
@staff_required
def dashboard():
    """Staff dashboard — overview of assigned treks with trekker counts."""
    assignments = TrekAssignment.query.filter_by(
        staff_id=current_user.id,
        is_active=True,
    ).all()

    # Build trek data with trekker counts
    trek_data = []
    total_trekkers = 0
    for assignment in assignments:
        trek = assignment.trek
        trekker_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.booking_status.in_(['pending', 'confirmed'])
        ).count()
        total_trekkers += trekker_count
        trek_data.append({
            'trek': trek,
            'trekker_count': trekker_count,
            'assignment': assignment,
        })

    stats = {
        'assigned_treks': len(assignments),
        'total_trekkers': total_trekkers,
        'open_treks': sum(1 for td in trek_data if td['trek'].status == 'open'),
        'ongoing_treks': sum(1 for td in trek_data if td['trek'].status == 'ongoing'),
    }

    return render_template('staff/dashboard.html', stats=stats, trek_data=trek_data)


# ── Profile ────────────────────────────────────────────────────────────
@staff_bp.route('/profile', methods=['GET', 'POST'])
@staff_required
def profile():
    """View and update staff profile."""
    staff_profile = StaffProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        # Update user fields
        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != current_user.email:
            existing = User.query.filter_by(email=new_email).first()
            if existing and existing.id != current_user.id:
                flash('Email is already registered by another user.', 'error')
                return render_template('staff/profile.html', profile=staff_profile)
            current_user.email = new_email

        # Update password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('staff/profile.html', profile=staff_profile)
            current_user.set_password(new_password)

        # Update profile fields
        if staff_profile:
            staff_profile.full_name = request.form.get('full_name', staff_profile.full_name).strip()
            staff_profile.phone = request.form.get('phone', '').strip() or None
            try:
                staff_profile.experience_years = int(request.form.get('experience_years', 0))
            except ValueError:
                staff_profile.experience_years = staff_profile.experience_years
            staff_profile.specialization = request.form.get('specialization', '').strip() or None
            staff_profile.bio = request.form.get('bio', '').strip() or None

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('staff_bp.profile'))

    return render_template('staff/profile.html', profile=staff_profile)


# ── Trek Detail ────────────────────────────────────────────────────────
@staff_bp.route('/trek/<int:trek_id>')
@staff_required
def trek_detail(trek_id):
    """View assigned trek detail with management actions."""
    trek, assignment = _get_assigned_trek_or_403(trek_id)
    if not trek:
        return redirect(url_for('staff_bp.dashboard'))

    # Get bookings/participants for this trek
    bookings = Booking.query.filter_by(trek_id=trek_id).order_by(Booking.created_at.desc()).all()

    # Build participant data with user info
    participants = []
    for booking in bookings:
        user = User.query.get(booking.user_id)
        participants.append({
            'booking': booking,
            'user': user,
        })

    stats = {
        'total_participants': len([p for p in participants if p['booking'].booking_status in ('pending', 'confirmed')]),
        'confirmed': len([p for p in participants if p['booking'].booking_status == 'confirmed']),
        'pending': len([p for p in participants if p['booking'].booking_status == 'pending']),
        'cancelled': len([p for p in participants if p['booking'].booking_status == 'cancelled']),
    }

    return render_template('staff/trek_detail.html', trek=trek, participants=participants, stats=stats)


# ── Update Trek Slots ──────────────────────────────────────────────────
@staff_bp.route('/trek/<int:trek_id>/update-slots', methods=['POST'])
@staff_required
def update_slots(trek_id):
    """Update available trek slots."""
    trek, assignment = _get_assigned_trek_or_403(trek_id)
    if not trek:
        return redirect(url_for('staff_bp.dashboard'))

    try:
        new_slots = int(request.form.get('available_slots', trek.available_slots))
        if new_slots < 0:
            flash('Available slots cannot be negative.', 'error')
            return redirect(url_for('staff_bp.trek_detail', trek_id=trek_id))
        if new_slots > trek.max_slots:
            flash(f'Available slots cannot exceed max slots ({trek.max_slots}).', 'error')
            return redirect(url_for('staff_bp.trek_detail', trek_id=trek_id))

        trek.available_slots = new_slots
        db.session.commit()
        flash(f'Available slots updated to {new_slots}.', 'success')
    except ValueError:
        flash('Invalid slot number provided.', 'error')

    return redirect(url_for('staff_bp.trek_detail', trek_id=trek_id))


# ── Update Trek Status ────────────────────────────────────────────────
@staff_bp.route('/trek/<int:trek_id>/update-status', methods=['POST'])
@staff_required
def update_status(trek_id):
    """Update trek status (Open/Closed/Started/Ongoing/Completed)."""
    trek, assignment = _get_assigned_trek_or_403(trek_id)
    if not trek:
        return redirect(url_for('staff_bp.dashboard'))

    new_status = request.form.get('status', trek.status)
    valid_statuses = ['open', 'closed', 'ongoing', 'completed', 'cancelled']

    if new_status not in valid_statuses:
        flash('Invalid status selected.', 'error')
        return redirect(url_for('staff_bp.trek_detail', trek_id=trek_id))

    old_status = trek.status
    trek.status = new_status
    db.session.commit()
    flash(f'Trek status changed from "{old_status}" to "{new_status}".', 'success')
    return redirect(url_for('staff_bp.trek_detail', trek_id=trek_id))


# ── Participants ───────────────────────────────────────────────────────
@staff_bp.route('/trek/<int:trek_id>/participants')
@staff_required
def participants(trek_id):
    """View registered users for a trek."""
    trek, assignment = _get_assigned_trek_or_403(trek_id)
    if not trek:
        return redirect(url_for('staff_bp.dashboard'))

    bookings = Booking.query.filter_by(trek_id=trek_id).order_by(Booking.created_at.desc()).all()

    participant_list = []
    for booking in bookings:
        user = User.query.get(booking.user_id)
        participant_list.append({
            'booking': booking,
            'user': user,
        })

    return render_template('staff/participants.html', trek=trek, participants=participant_list)
