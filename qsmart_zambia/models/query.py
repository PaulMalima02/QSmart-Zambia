from datetime import datetime
from utils.database import db


class CustomerQuery(db.Model):
    __tablename__ = 'queries'
    __table_args__ = (
        db.Index('ix_query_inst_status', 'institution_id', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('institution_branches.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    subject = db.Column(db.String(150))
    language = db.Column(db.String(20), default='en')
    status = db.Column(db.String(20), default='new', index=True)
    # new | assigned | in_progress | replied | resolved | closed

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('customer_queries', lazy='dynamic'))
    institution = db.relationship('Institution', backref=db.backref('queries', lazy='dynamic'))
    branch = db.relationship('InstitutionBranch')
    service = db.relationship('Service')
    assigned_staff = db.relationship('User', foreign_keys=[assigned_staff_id])
    messages = db.relationship('QueryMessage', backref='query', lazy='dynamic', cascade='all, delete-orphan',
                               order_by='QueryMessage.created_at')

    def __repr__(self):
        return f'<Query {self.reference}>'


class QueryMessage(db.Model):
    __tablename__ = 'query_messages'

    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('queries.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=True)
    voice_path = db.Column(db.String(255))
    attachment_path = db.Column(db.String(255))
    attachment_name = db.Column(db.String(200))
    attachment_type = db.Column(db.String(20))  # voice | image | document
    is_staff = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship('User')
