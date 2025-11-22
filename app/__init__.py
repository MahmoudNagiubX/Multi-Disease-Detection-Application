# App factory & basic config
from flask import Flask
from .routes import main_bp
from .core.managers.database_manager import db_manager

# Application factory function.
def create_app():
    # Tell Flask where templates and static files live
    app = Flask(
        __name__,
        template_folder = "ui/pages",   # HTML files
        static_folder = "ui"           # CSS files
    )

    # Secret key (needed later for sessions, flash messages, etc.)
    # For now it's a hardcoded string; later you can load it from env/config.
    app.config["SECRET_KEY"] = "change_this_later_to_a_random_secret"

    db_manager.init_db() # Initialize database

    # Register blueprints (route groups)
    app.register_blueprint(main_bp)
    return app
