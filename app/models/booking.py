"""
Trekk Management App — Booking Model

Defines the Booking model linking Users (Trekkers) to Treks.
"""

from datetime import datetime, timezone
from app import db


class Booking(db.Model):
    """
    Booking model representing a trekker's reservation for a trek.

    Booking Status:
        - pending: Booking is awaiting confirmation
        - confirmed: Booking is placed and held (displayed as "Booked")
        - cancelled: Booking has been cancelled
        - completed: The trek ran and this booking was fulfilled

    A booking reaches 'completed' when its trek is marked completed; it reaches
    'cancelled' either by the trekker or when its trek is cancelled.

    Payment Status:
        - unpaid: Payment has not been made
        - paid: Payment has been received
        - refunded: Payment was refunded (e.g., on cancellation)
    """
    __tablename__ = 'bookings'

    STATUSES = ('pending', 'confirmed', 'cancelled', 'completed')

    # Bookings that still hold a slot on the trek
    ACTIVE_STATUSES = ('pending', 'confirmed')

    # Bookings that belong in a trekker's trekking history
    HISTORY_STATUSES = ('completed', 'cancelled')

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    trek_id = db.Column(db.Integer, db.ForeignKey('treks.id'), nullable=False, index=True)
    booking_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    booking_status = db.Column(db.String(20), nullable=False, default='pending')  # pending | confirmed | cancelled | completed
    payment_status = db.Column(db.String(20), nullable=False, default='unpaid')  # unpaid | paid | refunded
    number_of_participants = db.Column(db.Integer, nullable=False, default=1)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)

    # ── Completion / cancellation details ──────────────────────────────
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ── Helper Methods ─────────────────────────────────────────────────
    @property
    def is_confirmed(self):
        """Check if the booking is confirmed."""
        return self.booking_status == 'confirmed'

    @property
    def is_paid(self):
        """Check if the booking has been paid."""
        return self.payment_status == 'paid'

    @property
    def is_active(self):
        """Check if the booking still holds a slot on the trek."""
        return self.booking_status in self.ACTIVE_STATUSES

    @property
    def is_completed(self):
        """Check if the booking was fulfilled."""
        return self.booking_status == 'completed'

    @property
    def status_label(self):
        """Human-facing status label (a held booking reads as 'Booked')."""
        return {'confirmed': 'Booked'}.get(self.booking_status, self.booking_status.title())

    def cancel(self):
        """Cancel the booking and mark payment as refunded if paid."""
        self.booking_status = 'cancelled'
        self.cancelled_at = datetime.now(timezone.utc)
        if self.payment_status == 'paid':
            self.payment_status = 'refunded'

    def mark_completed(self):
        """Mark the booking fulfilled once its trek has been completed."""
        self.booking_status = 'completed'
        self.completed_at = datetime.now(timezone.utc)

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self):
        """Convert booking to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'trek_id': self.trek_id,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'booking_status': self.booking_status,
            'payment_status': self.payment_status,
            'number_of_participants': self.number_of_participants,
            'total_amount': self.total_amount,
            'notes': self.notes,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Booking #{self.id} User:{self.user_id} Trek:{self.trek_id} ({self.booking_status})>'
