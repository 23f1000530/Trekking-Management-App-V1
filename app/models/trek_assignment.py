"""
Trekk Management App — Trek Assignment Model

Defines the TrekAssignment model for the many-to-many relationship
between Trek Staff (Users) and Treks.
"""

from datetime import datetime, timezone
from app import db


class TrekAssignment(db.Model):
    """
    Trek Assignment model representing the assignment of a staff member to a trek.
    This is an association table with extra data (assigned_date, is_active).

    Relationships:
        - Trek ↔ Staff (many-to-many via this table)
        - A staff member can be assigned to multiple treks.
        - A trek can have multiple staff members assigned.
    """
    __tablename__ = 'trek_assignments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    trek_id = db.Column(db.Integer, db.ForeignKey('treks.id'), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    assigned_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Unique Constraint ──────────────────────────────────────────────
    # Prevent duplicate assignments of the same staff to the same trek
    __table_args__ = (
        db.UniqueConstraint('trek_id', 'staff_id', name='uq_trek_staff_assignment'),
    )

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self):
        """Convert trek assignment to dictionary."""
        return {
            'id': self.id,
            'trek_id': self.trek_id,
            'staff_id': self.staff_id,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<TrekAssignment Trek:{self.trek_id} ↔ Staff:{self.staff_id} (Active:{self.is_active})>'
