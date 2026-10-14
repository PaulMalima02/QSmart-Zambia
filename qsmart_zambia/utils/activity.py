from flask import request
from utils.database import db
import re


def _scrub(text):
    """Mask phone-like and email-like tokens in audit detail."""
    text = re.sub(r'\+?260\d{9}', lambda m: m.group(0)[:4] + '****' + m.group(0)[-3:], text)
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', lambda m: m.group(0)[0] + '***@' + m.group(0).split('@')[-1], text)
    return text


def log_activity(action, user=None, detail=None, username=None):
    try:
        from models.notification import AuditLog
        ip = None
        try:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
        except Exception:
            pass
        entry = AuditLog(
            user_id=user.id if user else None,
            username=username or (user.username if user else None),
            action=action,
            detail=_scrub(detail or '')[:1000],
            ip_address=ip,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print('log_activity:', e)
