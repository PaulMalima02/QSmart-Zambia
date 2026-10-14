"""Data retention and deletion helpers — purpose limitation."""
from datetime import datetime, timedelta
from utils.database import db


def purge_old_audit_logs(days=365):
    from models.notification import AuditLog
    cutoff = datetime.utcnow() - timedelta(days=days)
    n = AuditLog.query.filter(AuditLog.created_at < cutoff).delete()
    db.session.commit()
    return n


def purge_old_sms_logs(days=180):
    from models.notification import SmsLog
    cutoff = datetime.utcnow() - timedelta(days=days)
    n = SmsLog.query.filter(SmsLog.created_at < cutoff).delete()
    db.session.commit()
    return n


def anonymize_user(user):
    """Right to erasure — keep audit integrity, remove PII."""
    user.full_name = 'Deleted User'
    user.email = f'deleted_{user.id}@erased.local'
    user.phone = None
    user.address = None
    user.is_active = False
    user.username = f'deleted_{user.id}'
    db.session.commit()
