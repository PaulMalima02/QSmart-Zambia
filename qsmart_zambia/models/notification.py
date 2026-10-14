from datetime import datetime
from utils.database import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text)
    link = db.Column(db.String(255))
    category = db.Column(db.String(40), default='general')  # queue | query | account | system
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))


class SmsLog(db.Model):
    __tablename__ = 'sms_log'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(30), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(40))  # queue_next | query_reply | approval | general
    related_ref = db.Column(db.String(40))
    status = db.Column(db.String(20), default='pending')  # pending | sent | failed | log_only
    provider_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    __table_args__ = (db.Index('ix_audit_created', 'created_at'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(50), nullable=False, index=True)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
