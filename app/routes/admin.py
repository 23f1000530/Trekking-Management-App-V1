"""
Trekk Management App — Admin Dashboard Routes

Admin-only routes for full system management:
- Dashboard with stats overview
- Trek CRUD (create, edit, delete)
- Staff management (approve, remove, assign to treks)
- User management (view, blacklist/activate)
- Booking records and trekking history
- Search across treks, staff, and users
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.utils.decorators import admin_required
from app.utils.trek_status import commit_status_change, ALLOWED_TRANSITIONS
from app import db
from app.models.user import User
from app.models.trek import Trek
from app.models.booking import Booking
from app.models.staff_profile import StaffProfile
from app.models.trek_assignment import TrekAssignment
from datetime import datetime

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


# ── Dashboard ──────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard — overview of system stats."""
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = User.query.filter_by(role='trek_staff').count()
    pending_staff = User.query.filter_by(role='trek_staff', is_approved=False).count()
    total_bookings = Booking.query.count()
    active_treks = Trek.query.filter(Trek.status.in_(['open', 'ongoing'])).count()

    stats = {
        'total_treks': total_treks,
        'total_users': total_users,
        'total_staff': total_staff,
        'pending_staff': pending_staff,
        'total_bookings': total_bookings,
        'active_treks': active_treks,
    }

    # Get recent bookings for the dashboard
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html', stats=stats, recent_bookings=recent_bookings)


# ── Trek Management ───────────────────────────────────────────────────
@admin_bp.route('/treks')
@admin_required
def treks():
    """List all treks with management and lifecycle actions."""
    all_treks = Trek.query.order_by(Trek.created_at.desc()).all()
    return render_template('admin/treks.html', treks=all_treks,
                           transitions=ALLOWED_TRANSITIONS)


@admin_bp.route('/treks/create', methods=['GET', 'POST'])
@admin_required
def create_trek():
    """Create a new trek."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        difficulty = request.form.get('difficulty', 'moderate')
        duration_days = request.form.get('duration_days', '1')
        max_slots = request.form.get('max_slots', '20')
        price = request.form.get('price', '0')
        location = request.form.get('location', '').strip()
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        image_url = request.form.get('image_url', '').strip()

        # Validation
        if not name:
            flash('Trek name is required.', 'error')
            return render_template('admin/trek_form.html', trek=None, action='create')

        try:
            duration_days = int(duration_days) if duration_days else 1
            max_slots = int(max_slots) if max_slots else 20
            price = float(price) if price else 0.0
        except ValueError:
            flash('Invalid numeric values provided.', 'error')
            return render_template('admin/trek_form.html', trek=None, action='create')

        trek = Trek(
            name=name,
            description=description if description else None,
            difficulty=difficulty,
            duration_days=duration_days,
            max_slots=max_slots,
            available_slots=max_slots,
            price=price,
            location=location if location else None,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
            image_url=image_url if image_url else None,
            status='pending',
        )

        db.session.add(trek)
        db.session.commit()
        flash(f'Trek "{name}" created and is pending approval. '
              f'Approve it, then open it to start taking bookings.', 'success')
        return redirect(url_for('admin_bp.treks'))

    return render_template('admin/trek_form.html', trek=None, action='create')


@admin_bp.route('/treks/<int:trek_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_trek(trek_id):
    """Edit an existing trek."""
    trek = Trek.query.get_or_404(trek_id)

    if request.method == 'POST':
        trek.name = request.form.get('name', trek.name).strip()
        trek.description = request.form.get('description', '').strip() or None
        trek.difficulty = request.form.get('difficulty', trek.difficulty)
        trek.location = request.form.get('location', '').strip() or None
        trek.image_url = request.form.get('image_url', '').strip() or None

        try:
            trek.duration_days = int(request.form.get('duration_days', trek.duration_days))
            new_max = int(request.form.get('max_slots', trek.max_slots))
            # Adjust available slots proportionally
            diff = new_max - trek.max_slots
            trek.max_slots = new_max
            trek.available_slots = max(0, trek.available_slots + diff)
            trek.price = float(request.form.get('price', trek.price))
        except ValueError:
            flash('Invalid numeric values provided.', 'error')
            return render_template('admin/trek_form.html', trek=trek, action='edit')

        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        trek.start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        trek.end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None

        if not trek.name:
            flash('Trek name is required.', 'error')
            return render_template('admin/trek_form.html', trek=trek, action='edit')

        db.session.commit()
        flash(f'Trek "{trek.name}" updated successfully!', 'success')
        return redirect(url_for('admin_bp.treks'))

    return render_template('admin/trek_form.html', trek=trek, action='edit')


@admin_bp.route('/treks/<int:trek_id>/delete', methods=['POST'])
@admin_required
def delete_trek(trek_id):
    """Delete a trek."""
    trek = Trek.query.get_or_404(trek_id)
    name = trek.name

    # Delete related assignments and bookings first
    TrekAssignment.query.filter_by(trek_id=trek_id).delete()
    Booking.query.filter_by(trek_id=trek_id).delete()

    db.session.delete(trek)
    db.session.commit()
    flash(f'Trek "{name}" has been deleted.', 'success')
    return redirect(url_for('admin_bp.treks'))


# ── Staff Management ──────────────────────────────────────────────────
@admin_bp.route('/staff')
@admin_required
def staff():
    """List all trek staff with management actions."""
    all_staff = User.query.filter_by(role='trek_staff').order_by(User.created_at.desc()).all()
    all_treks = Trek.query.filter(Trek.status.in_(['open', 'ongoing'])).order_by(Trek.name).all()
    return render_template('admin/staff.html', staff_list=all_staff, treks=all_treks)


@admin_bp.route('/staff/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_staff(user_id):
    """Approve a pending staff member."""
    user = User.query.get_or_404(user_id)
    if user.role != 'trek_staff':
        flash('User is not a trek staff member.', 'error')
        return redirect(url_for('admin_bp.staff'))

    user.is_approved = True
    db.session.commit()
    flash(f'Staff member "{user.username}" has been approved.', 'success')
    return redirect(url_for('admin_bp.staff'))


@admin_bp.route('/staff/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_staff(user_id):
    """Reject (delete) a pending staff member."""
    user = User.query.get_or_404(user_id)
    if user.role != 'trek_staff':
        flash('User is not a trek staff member.', 'error')
        return redirect(url_for('admin_bp.staff'))

    # Remove assignments
    TrekAssignment.query.filter_by(staff_id=user_id).delete()

    db.session.delete(user)
    db.session.commit()
    flash(f'Staff member "{user.username}" has been removed from the system.', 'success')
    return redirect(url_for('admin_bp.staff'))


@admin_bp.route('/staff/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_staff_active(user_id):
    """Blacklist/activate a staff member."""
    user = User.query.get_or_404(user_id)
    if user.role != 'trek_staff':
        flash('User is not a trek staff member.', 'error')
        return redirect(url_for('admin_bp.staff'))

    user.is_active = not user.is_active
    status = 'activated' if user.is_active else 'deactivated'
    db.session.commit()
    flash(f'Staff member "{user.username}" has been {status}.', 'success')
    return redirect(url_for('admin_bp.staff'))


@admin_bp.route('/staff/assign', methods=['POST'])
@admin_required
def assign_staff():
    """Assign a staff member to a trek."""
    staff_id = request.form.get('staff_id', type=int)
    trek_id = request.form.get('trek_id', type=int)

    if not staff_id or not trek_id:
        flash('Please select both a staff member and a trek.', 'error')
        return redirect(url_for('admin_bp.staff'))

    # Verify staff exists and is trek_staff
    staff_user = User.query.get(staff_id)
    if not staff_user or staff_user.role != 'trek_staff':
        flash('Invalid staff member selected.', 'error')
        return redirect(url_for('admin_bp.staff'))

    # Verify trek exists
    trek = Trek.query.get(trek_id)
    if not trek:
        flash('Invalid trek selected.', 'error')
        return redirect(url_for('admin_bp.staff'))

    # Check if already assigned
    existing = TrekAssignment.query.filter_by(
        staff_id=staff_id, trek_id=trek_id
    ).first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
            flash(f'"{staff_user.username}" re-assigned to "{trek.name}".', 'success')
        else:
            flash(f'"{staff_user.username}" is already assigned to "{trek.name}".', 'warning')
        return redirect(url_for('admin_bp.staff'))

    assignment = TrekAssignment(
        staff_id=staff_id,
        trek_id=trek_id,
        is_active=True,
    )
    db.session.add(assignment)
    db.session.commit()
    flash(f'"{staff_user.username}" assigned to "{trek.name}" successfully!', 'success')
    return redirect(url_for('admin_bp.staff'))


@admin_bp.route('/staff/unassign/<int:assignment_id>', methods=['POST'])
@admin_required
def unassign_staff(assignment_id):
    """Remove a staff assignment from a trek."""
    assignment = TrekAssignment.query.get_or_404(assignment_id)
    assignment.is_active = False
    db.session.commit()
    flash('Staff assignment has been removed.', 'success')
    return redirect(url_for('admin_bp.staff'))


# ── User Management ──────────────────────────────────────────────────
@admin_bp.route('/users')
@admin_required
def users():
    """List all trekker users with management actions."""
    all_users = User.query.filter_by(role='trekker').order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Blacklist/activate a trekker user."""
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot deactivate admin accounts.', 'error')
        return redirect(url_for('admin_bp.users'))

    user.is_active = not user.is_active
    status = 'activated' if user.is_active else 'blacklisted'
    db.session.commit()
    flash(f'User "{user.username}" has been {status}.', 'success')
    return redirect(url_for('admin_bp.users'))


# ── Trek Status Lifecycle ─────────────────────────────────────────────
@admin_bp.route('/treks/<int:trek_id>/status', methods=['POST'])
@admin_required
def update_trek_status(trek_id):
    """Move a trek through its lifecycle (pending → approved → open → … → completed)."""
    trek = Trek.query.get_or_404(trek_id)
    new_status = request.form.get('status', '')
    notes = request.form.get('completion_notes', '').strip() or None

    _, message, category = commit_status_change(
        trek, new_status, Trek.ADMIN_STATUSES, completion_notes=notes
    )
    flash(message, category)
    return redirect(request.referrer or url_for('admin_bp.treks'))


# ── Booking Management ────────────────────────────────────────────────
@admin_bp.route('/bookings')
@admin_required
def bookings():
    """View all booking records across every user."""
    all_bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=all_bookings)


# ── Trekking History ──────────────────────────────────────────────────
@admin_bp.route('/history')
@admin_required
def history():
    """
    Complete trekking history across all users, with filters.

    Unlike /bookings (a raw record list), this is the historical view: it can be
    narrowed to a single trekker, a single trek, or a booking status so an admin
    can answer "what has this user actually trekked?".
    """
    user_id = request.args.get('user_id', type=int)
    trek_id = request.args.get('trek_id', type=int)
    status = request.args.get('status', '')

    query = Booking.query

    if user_id:
        query = query.filter(Booking.user_id == user_id)
    if trek_id:
        query = query.filter(Booking.trek_id == trek_id)
    if status and status in Booking.STATUSES:
        query = query.filter(Booking.booking_status == status)

    records = query.order_by(Booking.created_at.desc()).all()

    history_data = []
    for booking in records:
        history_data.append({
            'booking': booking,
            'trek': Trek.query.get(booking.trek_id),
            'user': User.query.get(booking.user_id),
        })

    stats = {
        'total': len(records),
        'completed': sum(1 for b in records if b.booking_status == 'completed'),
        'cancelled': sum(1 for b in records if b.booking_status == 'cancelled'),
        'active': sum(1 for b in records if b.booking_status in Booking.ACTIVE_STATUSES),
    }

    return render_template(
        'admin/history.html',
        history_data=history_data,
        stats=stats,
        trekkers=User.query.filter_by(role='trekker').order_by(User.username).all(),
        treks=Trek.query.order_by(Trek.name).all(),
        statuses=Booking.STATUSES,
        sel_user=user_id,
        sel_trek=trek_id,
        sel_status=status,
    )


# ── Search ────────────────────────────────────────────────────────────
@admin_bp.route('/search')
@admin_required
def search():
    """Search treks, staff, or users by name or ID."""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')

    results = {
        'treks': [],
        'staff': [],
        'users': [],
    }

    if query:
        # Try to parse as ID
        try:
            search_id = int(query)
            is_id = True
        except ValueError:
            search_id = None
            is_id = False

        if category in ('all', 'treks'):
            trek_query = Trek.query
            if is_id:
                trek_query = trek_query.filter(
                    db.or_(Trek.id == search_id, Trek.name.ilike(f'%{query}%'))
                )
            else:
                trek_query = trek_query.filter(
                    db.or_(Trek.name.ilike(f'%{query}%'), Trek.location.ilike(f'%{query}%'))
                )
            results['treks'] = trek_query.all()

        if category in ('all', 'staff'):
            staff_query = User.query.filter_by(role='trek_staff')
            if is_id:
                staff_query = staff_query.filter(
                    db.or_(User.id == search_id, User.username.ilike(f'%{query}%'))
                )
            else:
                staff_query = staff_query.filter(
                    db.or_(User.username.ilike(f'%{query}%'), User.email.ilike(f'%{query}%'))
                )
            results['staff'] = staff_query.all()

        if category in ('all', 'users'):
            user_query = User.query.filter_by(role='trekker')
            if is_id:
                user_query = user_query.filter(
                    db.or_(User.id == search_id, User.username.ilike(f'%{query}%'))
                )
            else:
                user_query = user_query.filter(
                    db.or_(User.username.ilike(f'%{query}%'), User.email.ilike(f'%{query}%'))
                )
            results['users'] = user_query.all()

    return render_template('admin/search.html', query=query, category=category, results=results)
