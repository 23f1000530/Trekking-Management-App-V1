"""
Trekk Management App — Trekker Dashboard Routes

Trekker routes for browsing, booking, and managing trek reservations:
- Dashboard with booking stats and upcoming treks
- Profile update
- Browse available/open treks with search and filtering
- Book treks with duplicate and slot validation
- View booking history and trek status
- Cancel bookings
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.utils.decorators import trekker_required
from app import db
from app.models.user import User
from app.models.trek import Trek
from app.models.booking import Booking

trekker_bp = Blueprint('trekker_bp', __name__, url_prefix='/trekker')


# ── Dashboard ──────────────────────────────────────────────────────────
@trekker_bp.route('/dashboard')
@trekker_required
def dashboard():
    """Trekker dashboard — overview of bookings and upcoming treks."""
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()

    active_bookings = [b for b in my_bookings if b.booking_status in ('pending', 'confirmed')]
    completed_bookings = [b for b in my_bookings if b.booking_status == 'completed']
    cancelled_bookings = [b for b in my_bookings if b.booking_status == 'cancelled']

    stats = {
        'total_bookings': len(my_bookings),
        'active_bookings': len(active_bookings),
        'completed_bookings': len(completed_bookings),
        'cancelled_bookings': len(cancelled_bookings),
    }

    # Get upcoming booked treks (active bookings with trek details)
    upcoming_treks = []
    for booking in active_bookings:
        trek = Trek.query.get(booking.trek_id)
        if trek:
            upcoming_treks.append({
                'booking': booking,
                'trek': trek,
            })

    return render_template('trekker/dashboard.html', stats=stats,
                           upcoming_treks=upcoming_treks, bookings=my_bookings)


# ── Profile ────────────────────────────────────────────────────────────
@trekker_bp.route('/profile', methods=['GET', 'POST'])
@trekker_required
def profile():
    """View and update trekker profile."""
    if request.method == 'POST':
        # Update email
        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != current_user.email:
            existing = User.query.filter_by(email=new_email).first()
            if existing and existing.id != current_user.id:
                flash('Email is already registered by another user.', 'error')
                return render_template('trekker/profile.html')
            current_user.email = new_email

        # Update password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('trekker/profile.html')
            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('trekker_bp.profile'))

    return render_template('trekker/profile.html')


# ── Browse Treks ───────────────────────────────────────────────────────
@trekker_bp.route('/treks')
@trekker_required
def browse_treks():
    """Browse available/open treks with search and filtering."""
    search = request.args.get('search', '').strip()
    difficulty = request.args.get('difficulty', '')
    location = request.args.get('location', '').strip()
    sort_by = request.args.get('sort', 'newest')

    # Base query — only open treks
    query = Trek.query.filter(Trek.status == 'open')

    # Search by name
    if search:
        query = query.filter(
            db.or_(
                Trek.name.ilike(f'%{search}%'),
                Trek.description.ilike(f'%{search}%'),
                Trek.location.ilike(f'%{search}%'),
            )
        )

    # Filter by difficulty
    if difficulty and difficulty in ('easy', 'moderate', 'hard', 'extreme'):
        query = query.filter(Trek.difficulty == difficulty)

    # Filter by location
    if location:
        query = query.filter(Trek.location.ilike(f'%{location}%'))

    # Sorting
    if sort_by == 'price_low':
        query = query.order_by(Trek.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Trek.price.desc())
    elif sort_by == 'duration':
        query = query.order_by(Trek.duration_days.asc())
    elif sort_by == 'name':
        query = query.order_by(Trek.name.asc())
    else:  # newest
        query = query.order_by(Trek.created_at.desc())

    treks = query.all()

    # Get unique locations for filter dropdown
    all_locations = db.session.query(Trek.location).filter(
        Trek.status == 'open',
        Trek.location.isnot(None)
    ).distinct().all()
    locations = sorted([loc[0] for loc in all_locations if loc[0]])

    # Check which treks the user has already booked (active bookings)
    booked_trek_ids = set()
    active_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.booking_status.in_(['pending', 'confirmed'])
    ).all()
    for b in active_bookings:
        booked_trek_ids.add(b.trek_id)

    return render_template('trekker/browse_treks.html',
                           treks=treks,
                           search=search,
                           difficulty=difficulty,
                           location=location,
                           sort_by=sort_by,
                           locations=locations,
                           booked_trek_ids=booked_trek_ids)


# ── Trek Detail ────────────────────────────────────────────────────────
@trekker_bp.route('/treks/<int:trek_id>')
@trekker_required
def trek_detail(trek_id):
    """View trek details."""
    trek = Trek.query.get_or_404(trek_id)

    # Check if user already has an active booking for this trek
    existing_booking = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.trek_id == trek_id,
        Booking.booking_status.in_(['pending', 'confirmed'])
    ).first()

    return render_template('trekker/trek_detail.html', trek=trek, existing_booking=existing_booking)


# ── Book Trek ──────────────────────────────────────────────────────────
@trekker_bp.route('/treks/<int:trek_id>/book', methods=['POST'])
@trekker_required
def book_trek(trek_id):
    """Book a trek with validation."""
    trek = Trek.query.get_or_404(trek_id)

    # Validate trek is open
    if trek.status != 'open':
        flash('This trek is not currently accepting bookings.', 'error')
        return redirect(url_for('trekker_bp.trek_detail', trek_id=trek_id))

    # Validate slots available
    participants = request.form.get('participants', '1')
    try:
        num_participants = int(participants)
        if num_participants < 1:
            num_participants = 1
    except ValueError:
        num_participants = 1

    if trek.available_slots <= 0:
        flash('Sorry, this trek is fully booked. No slots available.', 'error')
        return redirect(url_for('trekker_bp.trek_detail', trek_id=trek_id))

    if num_participants > trek.available_slots:
        flash(f'Only {trek.available_slots} slot(s) available. Please reduce the number of participants.', 'error')
        return redirect(url_for('trekker_bp.trek_detail', trek_id=trek_id))

    # Check for duplicate booking
    existing_booking = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.trek_id == trek_id,
        Booking.booking_status.in_(['pending', 'confirmed'])
    ).first()

    if existing_booking:
        flash('You already have an active booking for this trek.', 'warning')
        return redirect(url_for('trekker_bp.trek_detail', trek_id=trek_id))

    # Calculate total amount
    total_amount = trek.price * num_participants

    # Create booking
    booking = Booking(
        user_id=current_user.id,
        trek_id=trek_id,
        booking_status='confirmed',
        payment_status='unpaid',
        number_of_participants=num_participants,
        total_amount=total_amount,
        notes=request.form.get('notes', '').strip() or None,
    )

    # Reduce available slots
    trek.book_slot(num_participants)

    db.session.add(booking)
    db.session.commit()

    flash(f'Successfully booked "{trek.name}"! {num_participants} participant(s), Total: ₹{total_amount:.0f}', 'success')
    return redirect(url_for('trekker_bp.my_bookings'))


# ── Cancel Booking ─────────────────────────────────────────────────────
@trekker_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@trekker_required
def cancel_booking(booking_id):
    """Cancel a booking."""
    booking = Booking.query.get_or_404(booking_id)

    # Ensure booking belongs to current user
    if booking.user_id != current_user.id:
        flash('You can only cancel your own bookings.', 'error')
        return redirect(url_for('trekker_bp.my_bookings'))

    # Ensure booking is cancellable
    if booking.booking_status not in ('pending', 'confirmed'):
        flash('This booking cannot be cancelled.', 'error')
        return redirect(url_for('trekker_bp.my_bookings'))

    # Release slots back to the trek
    trek = Trek.query.get(booking.trek_id)
    if trek:
        trek.release_slot(booking.number_of_participants)

    # Cancel the booking
    booking.cancel()
    db.session.commit()

    flash('Booking has been cancelled successfully.', 'success')
    return redirect(url_for('trekker_bp.my_bookings'))


# ── My Bookings ────────────────────────────────────────────────────────
@trekker_bp.route('/bookings')
@trekker_required
def my_bookings():
    """View all bookings and booking status."""
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()

    booking_data = []
    for booking in bookings:
        trek = Trek.query.get(booking.trek_id)
        booking_data.append({
            'booking': booking,
            'trek': trek,
        })

    return render_template('trekker/my_bookings.html', booking_data=booking_data)


# ── Trekking History ──────────────────────────────────────────────────
@trekker_bp.route('/history')
@trekker_required
def history():
    """View completed trekking history."""
    bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.booking_status.in_(['completed', 'cancelled'])
    ).order_by(Booking.created_at.desc()).all()

    history_data = []
    for booking in bookings:
        trek = Trek.query.get(booking.trek_id)
        history_data.append({
            'booking': booking,
            'trek': trek,
        })

    return render_template('trekker/history.html', history_data=history_data)
