"""
Trekk Management App — User Model

Defines the User model with role-based access control.
Roles: admin, trek_staff, trekker
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """
    User model representing all users in the system.

    Roles:
        - admin: System administrator (pre-created, no registration)
        - trek_staff: Trek guide/staff (must register and be approved by admin)
        - trekker: Regular user who books treks (self-registration)
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='trekker')  # admin | trek_staff | trekker
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # For blacklisting/deactivation
    is_approved = db.Column(db.Boolean, default=False, nullable=False)  # Staff approval by admin

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ──────────────────────────────────────────────────
    # One-to-Many: User → Bookings (a trekker can have many bookings)
    bookings = db.relationship('Booking', backref='user', lazy='dynamic',
                               foreign_keys='Booking.user_id')

    # One-to-One: User → StaffProfile (only for trek_staff users)
    staff_profile = db.relationship('StaffProfile', backref='user', uselist=False,
                                    cascade='all, delete-orphan')

    # One-to-Many: User → TrekAssignment (staff assigned to treks)
    trek_assignments = db.relationship('TrekAssignment', backref='staff', lazy='dynamic',
                                       foreign_keys='TrekAssignment.staff_id')

    # ── Password Methods ───────────────────────────────────────────────
    def set_password(self, password):
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # ── Role Checks ────────────────────────────────────────────────────
    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    @property
    def is_trek_staff(self):
        """Check if user has trek_staff role."""
        return self.role == 'trek_staff'

    @property
    def is_trekker(self):
        """Check if user has trekker role."""
        return self.role == 'trekker'

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self):
        """Convert user to dictionary (excludes password_hash)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
