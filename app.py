import os
from flask import Flask
from config import Config
from database import init_db
from services.auth_service import init_oauth

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # Initialize Database & OAuth
    init_db(app)
    init_oauth(app)

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.teacher_routes import teacher_bp
    from routes.student_routes import student_bp
    from routes.profile_routes import profile_bp
    from routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp)

    # Context Processors for global template variables
    @app.context_processor
    def inject_globals():
        return {
            "college": Config.COLLEGE_NAME,
            "college_short": Config.COLLEGE_SHORT,
            "days": Config.DAYS,
            "periods_year_1": Config.PERIODS_YEAR_1,
            "periods_other": Config.PERIODS_OTHER_YEARS,
            "lunch_year_1": Config.LUNCH_YEAR_1,
            "lunch_other": Config.LUNCH_OTHER_YEARS,
            "max_theory": Config.MAX_THEORY_COURSES,
            "max_lab": Config.MAX_LAB_COURSES,
        }

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8080)
