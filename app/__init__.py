# App factory & basic config
from flask import Flask
from markupsafe import Markup, escape
from .routes import main_bp
from .core.managers.database_manager import db_manager

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def nl2br(value: str) -> Markup:
    """
    Convert newlines to <br> tags in a safe way.
    First escapes HTML to prevent XSS, then replaces newlines with <br> tags.
    """
    if value is None:
        return Markup("")
    # First escape HTML to avoid injection, then replace newlines with <br>
    escaped = escape(str(value))
    return Markup(escaped.replace("\n", "<br>\n"))


# Application factory function.
def create_app():
    # Tell Flask where templates and static files live
    app = Flask(
        __name__,
        template_folder = "ui/pages",   # HTML files
        static_folder = "ui/static",    # CSS/JS files
        static_url_path = "/static"     # Explicitly set URL path
    )
    
    # Secret key (needed later for sessions, flash messages, etc.)
    # For now it's a hardcoded string; later you can load it from env/config.
    app.config["SECRET_KEY"] = "change_this_later_to_a_random_secret"
    
    # CSRF Configuration
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_CHECK_DEFAULT"] = False  # Don't check all requests by default
    app.config["WTF_CSRF_METHODS"] = ["POST", "PUT", "PATCH", "DELETE"]  # Only check these methods
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # No time limit for CSRF tokens
    
    csrf.init_app(app)

    # Register custom Jinja filters
    app.jinja_env.filters["nl2br"] = nl2br

    db_manager.init_db() # Initialize database

    # Register blueprints (route groups)
    app.register_blueprint(main_bp)
    return app
