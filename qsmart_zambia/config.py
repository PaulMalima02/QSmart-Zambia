import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR = BASE_DIR / 'static' / 'uploads'
(UPLOAD_DIR / 'voice').mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / 'images').mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / 'docs').mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass


def _database_uri():
    url = os.environ.get('DATABASE_URL') or ''
    # Render/Heroku sometimes use postgres:// — SQLAlchemy needs postgresql://
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url:
        return url
    return f'sqlite:///{INSTANCE_DIR / "qsmart.db"}'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-change-in-production-qsmart-zm'
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _uri = SQLALCHEMY_DATABASE_URI
    if _uri.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'check_same_thread': False}}
    else:
        # Postgres (Render / Railway) — recycle connections
        SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 300}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('FORCE_HTTPS', '').lower() in ('1', 'true', 'yes')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    MIN_PASSWORD_LENGTH = 8

    MAX_ADMIN_ACCOUNTS = int(os.environ.get('MAX_ADMIN_ACCOUNTS', '2'))

    SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'log')
    SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
    SMS_USERNAME = os.environ.get('SMS_USERNAME', 'sandbox')
    SMS_SENDER = os.environ.get('SMS_SENDER', 'QSMART')
    SMS_FROM_NUMBER = os.environ.get('SMS_FROM_NUMBER', '')

    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@qsmart.zm')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', '')
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')

    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', '5'))
    OTP_MAX_ATTEMPTS = int(os.environ.get('OTP_MAX_ATTEMPTS', '5'))
    OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get('OTP_RESEND_COOLDOWN_SECONDS', '60'))
    RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', '15'))

    UPLOAD_FOLDER = str(UPLOAD_DIR)
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024
    ALLOWED_VOICE = {'webm', 'ogg', 'mp3', 'wav', 'm4a', 'mpeg'}
    ALLOWED_IMAGES = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ALLOWED_DOCS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

    ITEMS_PER_PAGE = 25
    APP_NAME = 'QSMART Zambia'

    IDLE_TIMEOUT_MINUTES = int(os.environ.get('IDLE_TIMEOUT_MINUTES', '15'))
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('SESSION_MINUTES', '120')))

    AUDIT_RETENTION_DAYS = int(os.environ.get('AUDIT_RETENTION_DAYS', '365'))
    SMS_LOG_RETENTION_DAYS = int(os.environ.get('SMS_LOG_RETENTION_DAYS', '180'))
    PRIVACY_POLICY_VERSION = '1.0'
