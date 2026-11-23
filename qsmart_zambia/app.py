import os
from flask import Flask, render_template
from config import Config
from utils.database import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust proxy headers on Render / Railway / nginx (HTTPS + real IP)
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    except Exception:
        pass
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    try:
        from flask_wtf.csrf import CSRFProtect, generate_csrf
        csrf = CSRFProtect(app)

        @app.context_processor
        def inject_csrf():
            return {'csrf_token': generate_csrf}
    except ImportError:
        @app.context_processor
        def inject_csrf():
            return {'csrf_token': lambda: ''}

    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


    @app.before_request
    def enforce_idle_timeout():
        """Automatic logout on shared devices after idle period."""
        from flask_login import current_user, logout_user
        from flask import session, redirect, url_for, flash, request
        from datetime import datetime, timedelta
        # Skip static
        if request.endpoint and request.endpoint.startswith('static'):
            return
        if current_user.is_authenticated:
            idle_min = app.config.get('IDLE_TIMEOUT_MINUTES', 15)
            last = session.get('last_activity')
            now = datetime.utcnow()
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    if now - last_dt > timedelta(minutes=idle_min):
                        logout_user()
                        session.clear()
                        flash('Signed out due to inactivity (shared-device protection).', 'info')
                        return redirect(url_for('auth.login'))
                except Exception:
                    pass
            session['last_activity'] = now.isoformat()
            session.permanent = True

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "frame-ancestors 'self'"
        )
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Prevent back-button access to cached protected pages
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        data = {'app_name': app.config.get('APP_NAME', 'QSMART Zambia'), 'unread_count': 0}
        try:
            if current_user.is_authenticated:
                from models.notification import Notification
                data['unread_count'] = Notification.query.filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
        except Exception:
            pass
        return data

    # Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.customer_routes import customer_bp
    from routes.staff_routes import staff_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    with app.app_context():
        from models import (  # noqa: F401 — register models
            User, Institution, InstitutionBranch, Service, Counter,
            QueueTicket, CustomerQuery, QueryMessage,
            Notification, SmsLog, AuditLog,
        )
        db.create_all()
        try:
            from utils.migrate import ensure_schema
            ensure_schema(db)
        except Exception as e:
            print('migrate:', e)
        from utils.seed_data import seed_all
        seed_all(app)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
