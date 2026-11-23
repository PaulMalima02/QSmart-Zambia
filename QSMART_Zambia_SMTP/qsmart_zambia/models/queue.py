from datetime import datetime
from utils.database import db


class QueueTicket(db.Model):
    __tablename__ = 'queues'
    __table_args__ = (
        db.Index('ix_queue_service_status', 'service_id', 'status'),
        db.Index('ix_queue_user_status', 'user_id', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('institution_branches.id'), nullable=True)
    counter_id = db.Column(db.Integer, db.ForeignKey('counters.id'), nullable=True)

    status = db.Column(db.String(20), default='waiting', index=True)
    # waiting | called | serving | completed | cancelled | skipped
    position = db.Column(db.Integer)
    estimated_wait = db.Column(db.Integer)
    near_turn_sms_sent = db.Column(db.Boolean, default=False)
    next_sms_sent = db.Column(db.Boolean, default=False)

    joined_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    called_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    user = db.relationship('User', backref=db.backref('tickets', lazy='dynamic'))
    service = db.relationship('Service', backref=db.backref('tickets', lazy='dynamic'))
    institution = db.relationship('Institution')
    branch = db.relationship('InstitutionBranch')
    counter = db.relationship('Counter')

    def __repr__(self):
        return f'<Ticket {self.ticket_number} {self.status}>'
