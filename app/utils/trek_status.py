"""
Trekk Management App — Trek Status Lifecycle

Single source of truth for trek status transitions and the booking-status
cascade that follows them.

Lifecycle:

    pending ──▶ approved ──▶ open ◀──▶ closed ──▶ ongoing ──▶ completed
       │            │          │          │           │
       └────────────┴──────────┴──────────┴───────────┴──▶ cancelled

Completing or cancelling a trek is not just a field change on the trek: every
booking that still holds a slot has to move with it, otherwise trekkers keep
"active" bookings for treks that already finished and those treks never show up
in their trekking history.
"""

from app import db
from app.models.booking import Booking
from app.models.trek import Trek


# Legal transitions per current status. Terminal statuses map to ().
ALLOWED_TRANSITIONS = {
    'pending': ('approved', 'cancelled'),
    'approved': ('open', 'cancelled'),
    'open': ('closed', 'ongoing', 'cancelled'),
    'closed': ('open', 'ongoing', 'cancelled'),
    'ongoing': ('completed', 'cancelled'),
    'completed': (),
    'cancelled': (),
}


def active_bookings_for(trek):
    """All bookings on a trek that still hold a slot."""
    return Booking.query.filter(
        Booking.trek_id == trek.id,
        Booking.booking_status.in_(Booking.ACTIVE_STATUSES),
    ).all()


def can_transition(trek, new_status):
    """Check whether a trek may move to new_status from its current status."""
    return new_status in ALLOWED_TRANSITIONS.get(trek.status, ())


def apply_status_change(trek, new_status, allowed_statuses, completion_notes=None):
    """
    Validate and apply a trek status transition, cascading to its bookings.

    `allowed_statuses` scopes the transition to the caller's role — admins may
    approve a trek, assigned staff may only run one that is already approved.

    Returns (ok, message, flash_category). The caller commits on success.
    """
    if new_status not in Trek.STATUSES:
        return False, 'Invalid trek status selected.', 'error'

    if new_status not in allowed_statuses:
        return False, f'You are not permitted to set a trek to "{new_status}".', 'error'

    if new_status == trek.status:
        return False, f'Trek is already "{trek.status}".', 'info'

    if trek.is_terminal:
        return False, f'This trek is {trek.status} and can no longer be changed.', 'error'

    if not can_transition(trek, new_status):
        allowed = ', '.join(ALLOWED_TRANSITIONS.get(trek.status, ())) or 'nothing'
        return False, (f'Cannot move a "{trek.status}" trek to "{new_status}". '
                       f'Allowed next: {allowed}.'), 'error'

    old_status = trek.status
    cascaded = 0

    if new_status == 'approved':
        trek.approve()

    elif new_status == 'completed':
        trek.mark_completed(notes=completion_notes)
        # Every booking still holding a slot was fulfilled by this trek.
        for booking in active_bookings_for(trek):
            booking.mark_completed()
            cascaded += 1

    elif new_status == 'cancelled':
        trek.status = 'cancelled'
        # The trek is off; nobody is going, so release every held booking.
        for booking in active_bookings_for(trek):
            booking.cancel()
            cascaded += 1

    else:
        trek.status = new_status

    message = f'Trek status changed from "{old_status}" to "{new_status}".'
    if cascaded:
        moved = 'completed' if new_status == 'completed' else 'cancelled'
        message += f' {cascaded} booking(s) marked {moved}.'

    return True, message, 'success'


def commit_status_change(trek, new_status, allowed_statuses, completion_notes=None):
    """Apply a status change and commit it. Returns (ok, message, category)."""
    ok, message, category = apply_status_change(
        trek, new_status, allowed_statuses, completion_notes
    )
    if ok:
        db.session.commit()
    else:
        db.session.rollback()
    return ok, message, category
