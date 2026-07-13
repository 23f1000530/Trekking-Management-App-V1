"""
Trekk Management App — Admin Seed Script

Pre-creates the Admin user programmatically using SQLAlchemy ORM.
Run this script after initializing the database to ensure the Admin account exists.

Usage:
    python seed_admin.py
"""

from app import create_app, db
from app.models.user import User
from config import Config


def seed_admin():
    """Create the default Admin user if it doesn't already exist."""
    app = create_app()

    with app.app_context():
        # Create all tables (in case migrations haven't been run)
        db.create_all()

        # Check if admin already exists
        existing_admin = User.query.filter_by(role='admin').first()

        if existing_admin:
            print(f'[OK] Admin user already exists: {existing_admin.username} ({existing_admin.email})')
            return

        # Create the admin user
        admin = User(
            username=Config.ADMIN_USERNAME,
            email=Config.ADMIN_EMAIL,
            role='admin',
            is_active=True,
            is_approved=True,
        )
        admin.set_password(Config.ADMIN_PASSWORD)

        db.session.add(admin)
        db.session.commit()

        print('=' * 50)
        print('[SUCCESS] Admin user created successfully!')
        print('=' * 50)
        print(f'   Username : {Config.ADMIN_USERNAME}')
        print(f'   Email    : {Config.ADMIN_EMAIL}')
        print(f'   Password : {Config.ADMIN_PASSWORD}')
        print(f'   Role     : admin')
        print('=' * 50)
        print('[WARNING] Change the default password in production!')
        print('=' * 50)


if __name__ == '__main__':
    seed_admin()
