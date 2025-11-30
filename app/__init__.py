from logging.config import dictConfig
import babel
# GABUNGKAN import flask dan flask_login di sini untuk menghindari duplikasi
from flask import Flask, redirect, url_for, session, flash
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

__version__ = "0.1.0"

db = SQLAlchemy()
migrate = Migrate(compare_type=True)
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(
        __name__,
        static_url_path="/assets",
        static_folder="assets",
    )

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                },
                "simpleformatter": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
            },
            "handlers": {
                "custom_handler": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "filename": "warnings.log",
                    "level": "WARN",
                }
            },
            "root": {"level": "WARN", "handlers": ["custom_handler"]},
        }
    )

    app.config.from_pyfile("settings.py")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    
    # --- SINGLE SESSION CHECK ---
    @app.before_request
    def check_user_session():
        # Pastikan user sudah login dan role-nya peserta didik
        if current_user.is_authenticated and getattr(current_user, 'role', '') == 'peserta_didik':
            # Ambil token dari session browser
            browser_token = session.get('session_token')
            
            # Ambil token dari database (current_user otomatis refresh dari DB via user_loader)
            db_token = getattr(current_user, 'session_token', None)

            # Logika validasi:
            # 1. Jika token di DB kosong (berarti di-logout paksa admin)
            # 2. Jika token browser berbeda dengan DB (berarti login di tempat lain)
            if db_token is None or browser_token != db_token:
                logout_user()
                session.clear()
                flash("Sesi anda telah berakhir atau anda login di perangkat lain.", "error")
                return redirect(url_for('auth.login'))
    # ----------------------------

    @app.route("/", methods=["GET"])
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        elif current_user.role == "admin":
            return redirect(url_for("lesson.show"))
        elif current_user.role == "pembuat_soal":
            return redirect(url_for("lesson.show"))
        elif current_user.role == "proktor":
            return redirect(url_for("exam.show"))
        elif current_user.role == "peserta_didik":
            return redirect(url_for("doing.code"))

    @app.template_filter()
    def format_datetime(value, format="full"):
        if format == "full":
            format = "dd/MM/y HH:mm"
        elif format == "date":
            format = "dd/MM/y"
        elif format == "time":
            format = "HH:mm"
        return babel.dates.format_datetime(value, format)

    from app.controllers import (
        admin,
        api,
        auth,
        doing,
        error_handler,
        exam,
        image,
        lesson,
        rombel,
        school,
        student,
        sync,
    )

    app.register_blueprint(error_handler.bp)
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(auth.bp, url_prefix="/auth")
    app.register_blueprint(doing.bp, url_prefix="/doing")
    app.register_blueprint(exam.bp, url_prefix="/exam")
    app.register_blueprint(image.bp, url_prefix="/image")
    app.register_blueprint(lesson.bp, url_prefix="/lesson")
    app.register_blueprint(student.bp, url_prefix="/student")
    app.register_blueprint(school.bp, url_prefix="/school")
    app.register_blueprint(rombel.bp, url_prefix="/rombel")
    app.register_blueprint(api.bp, url_prefix="/api")
    app.register_blueprint(sync.bp, url_prefix="/sync")

    from app.commands.user import user_cli
    from app.commands.tool import tool_cli

    app.cli.add_command(user_cli)
    app.cli.add_command(tool_cli)

    return app

from app import models