"""
Trekk Management App — Trek Model

Defines the Trek model representing individual trekking expeditions.
"""

from datetime import datetime, timezone
from app import db


class Trek(db.Model):
    """
    Trek model representing a trekking expedition.

    Status lifecycle:
        pending → approved → open → closed → ongoing → completed
                                  ↘ cancelled (from any pre-completed state)

        - pending: Newly created by admin, not yet reviewed
        - approved: Admin has approved the trek, not yet published for booking
        - open: Trek is accepting bookings (the ONLY bookable status)
        - closed: Bookings are closed, trek has not started
        - ongoing: Trek is currently in progress
        - completed: Trek has finished (completion details recorded)
        - cancelled: Trek has been cancelled
    """
    __tablename__ = 'treks'

    # Full status vocabulary
    STATUSES = ('pending', 'approved', 'open', 'closed', 'ongoing', 'completed', 'cancelled')

    # Statuses an admin controls (lifecycle gate before a trek can be published)
    ADMIN_STATUSES = ('pending', 'approved', 'open', 'closed', 'ongoing', 'completed', 'cancelled')

    # Statuses assigned staff may set on a trek they run (cannot un-approve/re-gate a trek)
    STAFF_STATUSES = ('open', 'closed', 'ongoing', 'completed', 'cancelled')

    # Terminal statuses — no further transitions allowed
    TERMINAL_STATUSES = ('completed', 'cancelled')

    # The only status in which a trek accepts bookings
    BOOKABLE_STATUS = 'open'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), nullable=False, default='moderate')  # easy | moderate | hard | extreme
    duration_days = db.Column(db.Integer, nullable=False, default=1)
    max_slots = db.Column(db.Integer, nullable=False, default=20)
    available_slots = db.Column(db.Integer, nullable=False, default=20)
    price = db.Column(db.Float, nullable=False, default=0.0)
    location = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # see STATUSES
    image_url = db.Column(db.String(500), nullable=True)

    # ── Completion / lifecycle details ─────────────────────────────────
    approved_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    completion_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ──────────────────────────────────────────────────
    # One-to-Many: Trek → Bookings (a trek can have many bookings)
    bookings = db.relationship('Booking', backref='trek', lazy='dynamic',
                               foreign_keys='Booking.trek_id')

    # One-to-Many: Trek → TrekAssignment (a trek can have many assigned staff)
    assigned_staff = db.relationship('TrekAssignment', backref='trek', lazy='dynamic',
                                     foreign_keys='TrekAssignment.trek_id')

    # ── Helper Methods ─────────────────────────────────────────────────
    @property
    def is_full(self):
        """Check if the trek has no available slots."""
        return self.available_slots <= 0

    @property
    def is_open(self):
        """Check if the trek is currently accepting bookings."""
        return self.status == self.BOOKABLE_STATUS and not self.is_full

    @property
    def is_bookable(self):
        """A trek accepts bookings only when status is 'open' and slots remain."""
        return self.status == self.BOOKABLE_STATUS and self.available_slots > 0

    @property
    def is_terminal(self):
        """Check if the trek has reached a final state."""
        return self.status in self.TERMINAL_STATUSES

    @property
    def booked_slots(self):
        """Number of slots currently taken."""
        return self.max_slots - self.available_slots

    def approve(self):
        """Admin approval — moves a pending trek to approved and stamps the time."""
        self.status = 'approved'
        self.approved_at = datetime.now(timezone.utc)

    def mark_completed(self, notes=None):
        """Mark the trek completed and record completion details."""
        self.status = 'completed'
        self.completed_at = datetime.now(timezone.utc)
        if notes:
            self.completion_notes = notes

    def book_slot(self, count=1):
        """
        Reduce available slots by the given count.
        Returns True if successful, False if not enough slots.
        """
        if self.available_slots >= count:
            self.available_slots -= count
            return True
        return False

    def release_slot(self, count=1):
        """Release slots back (e.g., on cancellation)."""
        self.available_slots = min(self.available_slots + count, self.max_slots)

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self):
        """Convert trek to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'difficulty': self.difficulty,
            'duration_days': self.duration_days,
            'max_slots': self.max_slots,
            'available_slots': self.available_slots,
            'price': self.price,
            'location': self.location,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'image_url': self.image_url,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completion_notes': self.completion_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Trek {self.name} ({self.status})>'
