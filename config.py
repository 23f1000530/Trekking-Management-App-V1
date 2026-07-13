import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class for the Trekk Management App."""

    # Secret key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'trekk-management-secret-key-change-in-production'

    # SQLite database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'trekk_management.db')

    # Disable modification tracking (saves memory)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin default credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_EMAIL = 'admin@trekk.com'
    ADMIN_PASSWORD = 'admin123'
