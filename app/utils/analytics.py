"""
Trekk Management App — Dashboard Analytics

Aggregate queries backing the Chart.js dashboards.

Everything here aggregates in SQL (COUNT / SUM + GROUP BY) and returns one row
per bucket, rather than pulling rows into Python and counting them in a loop.
That matters: the staff dashboard used to run one COUNT per assigned trek
(an N+1), which these replace with a single grouped query.

Each role has exactly one entry point (admin_analytics / staff_analytics /
trekker_analytics) so a dashboard costs one round of queries, not one per chart.

NOTE: the month buckets use SQLite's strftime(). If this app is ever moved to
Postgres, swap those for date_trunc().
"""

from sqlalchemy import case, func

from app import db
from app.models.booking import Booking
from app.models.trek import Trek
from app.models.trek_assignment import TrekAssignment
from app.models.user import User

# Bookings that represent real money / a real seat.
REVENUE_STATUSES = ('confirmed', 'completed')

STATUS_LABELS = {
    'confirmed': 'Booked',
    'pending': 'Pending',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
}


def _month_expr(column):
    """Group key: 'YYYY-MM' (SQLite)."""
    return func.strftime('%Y-%m', column)


def _as_series(rows, label_map=None):
    """Turn [(key, value), ...] into the {labels, data} shape Chart.js wants."""
    labels, data = [], []
    for key, value in rows:
        key = key or 'unknown'
        labels.append((label_map or {}).get(key, str(key).title()))
        data.append(float(value or 0))
    return {'labels': labels, 'data': data}


def _fill_months(rows, months=6):
    """
    Pad a ('YYYY-MM', value) series so every one of the last `months` buckets
    appears, even the empty ones — otherwise a quiet month silently vanishes
    from the trend chart and the shape of the trend lies.
    """
    from datetime import date

    found = {key: float(value or 0) for key, value in rows if key}

    today = date.today()
    keys = []
    year, month = today.year, today.month
    for _ in range(months):
        keys.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    keys.reverse()

    names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    labels = [f'{names[int(k[5:7]) - 1]} {k[2:4]}' for k in keys]
    return {'labels': labels, 'data': [found.get(k, 0.0) for k in keys]}


# ── Admin ──────────────────────────────────────────────────────────────
def admin_analytics():
    """System-wide totals, distributions, and revenue trend."""
    # One pass over users, bucketed by role AND approval, so we get the role
    # totals and the pending-staff count from the same query.
    user_rows = db.session.query(
        User.role, User.is_approved, func.count(User.id)
    ).group_by(User.role, User.is_approved).all()

    role_totals = {}
    pending_staff = 0
    for role, approved, count in user_rows:
        role_totals[role] = role_totals.get(role, 0) + count
        if role == 'trek_staff' and not approved:
            pending_staff += count

    # One pass over treks, bucketed by status.
    trek_rows = dict(
        db.session.query(Trek.status, func.count(Trek.id))
        .group_by(Trek.status).all()
    )

    # One pass over bookings: count per status AND revenue per status together.
    booking_rows = db.session.query(
        Booking.booking_status,
        func.count(Booking.id),
        func.coalesce(func.sum(Booking.total_amount), 0.0),
    ).group_by(Booking.booking_status).all()

    booking_counts = {status: count for status, count, _ in booking_rows}
    revenue = sum(amount for status, _, amount in booking_rows
                  if status in REVENUE_STATUSES)

    monthly = db.session.query(
        _month_expr(Booking.created_at),
        func.coalesce(func.sum(
            case((Booking.booking_status.in_(REVENUE_STATUSES), Booking.total_amount),
                 else_=0.0)
        ), 0.0),
    ).group_by(_month_expr(Booking.created_at)).all()

    return {
        'totals': {
            'total_treks': sum(trek_rows.values()),
            'total_users': role_totals.get('trekker', 0),
            'total_staff': role_totals.get('trek_staff', 0),
            'pending_staff': pending_staff,
            'open_treks': trek_rows.get('open', 0),
            'completed_treks': trek_rows.get('completed', 0),
            'active_treks': trek_rows.get('open', 0) + trek_rows.get('ongoing', 0),
            'total_bookings': sum(booking_counts.values()),
            'revenue': round(revenue, 2),
        },
        'booking_status': _as_series(
            [(s, booking_counts.get(s, 0)) for s in Booking.STATUSES],
            STATUS_LABELS,
        ),
        'trek_status': _as_series(
            [(s, trek_rows.get(s, 0)) for s in Trek.STATUSES]
        ),
        'monthly_revenue': _fill_months(monthly),
    }


# ── Staff ──────────────────────────────────────────────────────────────
def staff_analytics(staff_id):
    """Scoped to the treks this staff member is actually assigned to."""
    assigned_ids = [
        row[0] for row in
        db.session.query(TrekAssignment.trek_id)
        .filter(TrekAssignment.staff_id == staff_id,
                TrekAssignment.is_active.is_(True))
        .all()
    ]

    empty = {'labels': [], 'data': []}
    if not assigned_ids:
        return {
            'totals': {'assigned_treks': 0, 'total_participants': 0,
                       'active_treks': 0, 'completed_treks': 0, 'total_bookings': 0},
            'participants_per_trek': empty,
            'booking_status': empty,
        }

    trek_rows = dict(
        db.session.query(Trek.status, func.count(Trek.id))
        .filter(Trek.id.in_(assigned_ids))
        .group_by(Trek.status).all()
    )

    # Participants per trek — a single grouped join, replacing the old
    # one-COUNT-per-trek loop.
    per_trek = db.session.query(
        Trek.name,
        func.coalesce(func.sum(
            case((Booking.booking_status.in_(Booking.ACTIVE_STATUSES),
                  Booking.number_of_participants), else_=0)
        ), 0),
    ).select_from(Trek).outerjoin(
        Booking, Booking.trek_id == Trek.id
    ).filter(Trek.id.in_(assigned_ids)).group_by(Trek.id, Trek.name).order_by(Trek.name).all()

    booking_counts = dict(
        db.session.query(Booking.booking_status, func.count(Booking.id))
        .filter(Booking.trek_id.in_(assigned_ids))
        .group_by(Booking.booking_status).all()
    )

    return {
        'totals': {
            'assigned_treks': len(assigned_ids),
            'total_participants': int(sum(v for _, v in per_trek)),
            'active_treks': trek_rows.get('open', 0) + trek_rows.get('ongoing', 0),
            'completed_treks': trek_rows.get('completed', 0),
            'total_bookings': sum(booking_counts.values()),
        },
        'participants_per_trek': _as_series(per_trek),
        'booking_status': _as_series(
            [(s, booking_counts.get(s, 0)) for s in Booking.STATUSES],
            STATUS_LABELS,
        ),
    }


# ── Trekker ────────────────────────────────────────────────────────────
def trekker_analytics(user_id):
    """Scoped to one trekker — they can only ever see their own record."""
    rows = db.session.query(
        Booking.booking_status,
        func.count(Booking.id),
        func.coalesce(func.sum(Booking.total_amount), 0.0),
    ).filter(Booking.user_id == user_id).group_by(Booking.booking_status).all()

    counts = {status: count for status, count, _ in rows}
    spend = {status: amount for status, _, amount in rows}

    # Days actually trekked = duration of the treks they completed.
    days = db.session.query(
        func.coalesce(func.sum(Trek.duration_days), 0)
    ).select_from(Booking).join(Trek, Trek.id == Booking.trek_id).filter(
        Booking.user_id == user_id,
        Booking.booking_status == 'completed',
    ).scalar()

    monthly_count = db.session.query(
        _month_expr(Booking.created_at), func.count(Booking.id)
    ).filter(Booking.user_id == user_id).group_by(_month_expr(Booking.created_at)).all()

    monthly_spend = db.session.query(
        _month_expr(Booking.created_at),
        func.coalesce(func.sum(
            case((Booking.booking_status.in_(REVENUE_STATUSES), Booking.total_amount),
                 else_=0.0)
        ), 0.0),
    ).filter(Booking.user_id == user_id).group_by(_month_expr(Booking.created_at)).all()

    return {
        'totals': {
            'completed_treks': counts.get('completed', 0),
            'cancelled': counts.get('cancelled', 0),
            'active_bookings': sum(counts.get(s, 0) for s in Booking.ACTIVE_STATUSES),
            'total_bookings': sum(counts.values()),
            'days_trekked': int(days or 0),
            'total_spent': round(sum(spend.get(s, 0.0) for s in REVENUE_STATUSES), 2),
        },
        'history': _as_series(
            [(s, counts.get(s, 0)) for s in Booking.STATUSES],
            STATUS_LABELS,
        ),
        'monthly_bookings': _fill_months(monthly_count),
        'monthly_spend': _fill_months(monthly_spend),
    }
