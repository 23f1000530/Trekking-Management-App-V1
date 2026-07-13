"""
Trekk Management App — Flask Application Factory

Initializes the Flask app, extensions (SQLAlchemy, Migrate, Login Manager),
and registers blueprints.
"""

from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from config import Config

# Initialize extensions (created here, bound to app in create_app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_class=Config):
    """
    Application factory pattern.
    Creates and configures the Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Import models so they are registered with SQLAlchemy
    from app import models  # noqa: F401

    # User loader callback for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Register Blueprints ────────────────────────────────────────
    from app.routes.auth import auth
    from app.routes.admin import admin_bp
    from app.routes.staff import staff_bp
    from app.routes.trekker import trekker_bp

    app.register_blueprint(auth)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(trekker_bp)

    # ── Root Route ─────────────────────────────────────────────────
    @app.route('/')
    def index():
        """Redirect to appropriate dashboard or login page."""
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin_bp.dashboard'))
            elif current_user.is_trek_staff:
                return redirect(url_for('staff_bp.dashboard'))
            else:
                return redirect(url_for('trekker_bp.dashboard'))
        return redirect(url_for('auth.login'))

    # ── Error Handlers ─────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    return app
