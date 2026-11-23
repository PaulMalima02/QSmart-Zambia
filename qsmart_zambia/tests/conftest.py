import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key-not-for-production'
os.environ['SMS_PROVIDER'] = 'log'
os.environ['SMS_API_KEY'] = ''
os.environ['EMAIL_PROVIDER'] = ''
os.environ['RESEND_API_KEY'] = ''
os.environ['MAIL_SERVER'] = ''
os.environ['FLASK_ENV'] = 'testing'
os.environ['WTF_CSRF_ENABLED'] = 'false'
os.environ.setdefault('ADMIN_USERNAME', 'admin')
os.environ.setdefault('ADMIN_PASSWORD', 'Admin123!')
os.environ.setdefault('ADMIN_EMAIL', 'admin@qsmart.zm')


@pytest.fixture()
def app():
    from app import create_app
    from config import Config

    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SMS_PROVIDER = 'log'
        EMAIL_PROVIDER = ''
        MAIL_SERVER = ''
        RESEND_API_KEY = ''
        SECRET_KEY = 'test-secret'

    application = create_app(TestConfig)
    application.config['WTF_CSRF_ENABLED'] = False
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    from utils.database import db
    with app.app_context():
        yield db.session
