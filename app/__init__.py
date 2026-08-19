from flask import Flask
from flask_login import current_user

from .config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from .main import bp as main_bp
    from .auth import bp as auth_bp
    from .todos import bp as todos_bp
    from .settings import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(todos_bp)
    app.register_blueprint(settings_bp)

    @app.context_processor
    def inject_auth_state():
        return {
            "logged_in": current_user.is_authenticated,
            "user_email": current_user.email if current_user.is_authenticated else None,
            "theme": current_user.theme if current_user.is_authenticated else "dark",
        }

    with app.app_context():
        db.create_all()

    return app
