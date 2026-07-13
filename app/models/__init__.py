"""
Trekk Management App — Models Package

Imports all models so that Flask-Migrate (Alembic) can detect them
and generate proper migration scripts.
"""

from app.models.user import User
from app.models.trek import Trek
from app.models.booking import Booking
from app.models.staff_profile import StaffProfile
from app.models.trek_assignment import TrekAssignment

__all__ = ['User', 'Trek', 'Booking', 'StaffProfile', 'TrekAssignment']
