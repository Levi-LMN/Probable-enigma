# ============================================================================
# FILE: app.py - Application Factory
# ============================================================================
import os
import secrets
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth

# Initialize extensions
db = SQLAlchemy()
oauth = OAuth()


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Configuration
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
    app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL')
    app.config['TRACK_VISITS'] = True
    app.config['IGNORE_PATHS'] = ['/static', '/favicon.ico', '/robots.txt', '/sitemap.xml']

    # Create directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'projects'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'experience'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    oauth.init_app(app)

    # Configure Google OAuth
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Register blueprints
    from blueprints.public import public_bp
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Context processors
    @app.context_processor
    def inject_globals():
        from models import Project, WorkExperience
        return {
            'current_year': datetime.now().year,
            'now': datetime.utcnow,
            'projects_count': Project.query.filter_by(is_visible=True).count(),
            'experiences_count': WorkExperience.query.filter_by(is_visible=True).count()
        }

    # Visitor tracking
    @app.before_request
    def track_visit():
        from flask import request, session
        from models import PageVisit, DailyStats
        from datetime import date

        if not app.config['TRACK_VISITS'] or request.method != 'GET':
            return

        for ignore_path in app.config['IGNORE_PATHS']:
            if request.path.startswith(ignore_path):
                return

        if request.path.startswith('/admin'):
            return

        try:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            user_agent = request.headers.get('User-Agent', '')
            referrer = request.headers.get('Referer', '')

            page_visit = PageVisit(
                path=request.path,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                query_string=request.query_string.decode('utf-8')
            )
            db.session.add(page_visit)

            today = date.today()
            daily_stat = DailyStats.query.filter_by(date=today).first()

            if not daily_stat:
                daily_stat = DailyStats(date=today, total_visits=0, unique_visitors=0)
                db.session.add(daily_stat)
                db.session.flush()  # flush so the object is populated before we increment

            # Guard against NULL column values (e.g. after a manual DB edit)
            daily_stat.total_visits = (daily_stat.total_visits or 0) + 1

            if 'visitor_tracked' not in session:
                daily_stat.unique_visitors = (daily_stat.unique_visitors or 0) + 1
                session['visitor_tracked'] = True

            db.session.commit()

        except Exception as e:
            app.logger.error(f"Error tracking visit: {e}")
            db.session.rollback()

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app