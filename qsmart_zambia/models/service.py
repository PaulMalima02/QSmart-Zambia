from datetime import datetime
from utils.database import db


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('institution_branches.id'), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    avg_service_time = db.Column(db.Integer, default=10)  # minutes
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('InstitutionBranch', backref=db.backref('services', lazy='dynamic'))
    counters = db.relationship('Counter', backref='service', lazy='dynamic')

    def __repr__(self):
        return f'<Service {self.name}>'


class Counter(db.Model):
    __tablename__ = 'counters'

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    name = db.Column(db.String(80), nullable=False)
    is_open = db.Column(db.Boolean, default=True, index=True)
    current_ticket = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    institution = db.relationship('Institution', backref=db.backref('counters', lazy='dynamic'))
