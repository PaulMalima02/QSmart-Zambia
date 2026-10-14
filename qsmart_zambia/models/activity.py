from datetime import datetime
from utils.database import db


class ActivityLog(db.Model):
    """Audit trail of important system events for the system admin."""
    __tablename__ = 'activity_logs'
    __table_args__ = (
        db.Index('ix_activity_created', 'created_at'),
        db.Index('ix_activity_action', 'action'),
        db.Index('ix_activity_user', 'user_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(80))  # denormalised for history if user deleted
    action = db.Column(db.String(50), nullable=False, index=True)
    # register | staff_register | login | staff_login | logout |
    # staff_approved | staff_rejected | staff_revoked |
    # join_queue | call_ticket | complete_ticket | cancel_ticket | query_submit | query_reply
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))

    def __repr__(self):
        return f'<Activity {self.action} {self.username} @ {self.created_at}>'
