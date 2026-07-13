"""
Trekk Management App — Staff Profile Model

Defines the StaffProfile model for additional trek staff information.
One-to-one relationship with User (only for users with role='trek_staff').
"""

from datetime import datetime, timezone
from app import db


class StaffProfile(db.Model):
    """
    Staff Profile model storing additional details for trek staff members.
    Each staff profile is linked to exactly one User (one-to-one).
    """
    __tablename__ = 'staff_profiles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    experience_years = db.Column(db.Integer, nullable=True, default=0)
    specialization = db.Column(db.String(200), nullable=True)  # e.g., "High altitude treks", "River rafting"
    bio = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self):
        """Convert staff profile to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'phone': self.phone,
            'experience_years': self.experience_years,
            'specialization': self.specialization,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<StaffProfile {self.full_name} (User:{self.user_id})>'
