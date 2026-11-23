from datetime import datetime
from utils.database import db


class Institution(db.Model):
    __tablename__ = 'institutions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    code = db.Column(db.String(30), unique=True, index=True)
    category = db.Column(db.String(40), default='government', index=True)
    # hospital | bank | government | utility
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branches = db.relationship('InstitutionBranch', backref='institution', lazy='dynamic', cascade='all, delete-orphan')
    services = db.relationship('Service', backref='institution', lazy='dynamic')

    def __repr__(self):
        return f'<Institution {self.name}>'


class InstitutionBranch(db.Model):
    __tablename__ = 'institution_branches'

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)  # e.g. Lusaka Main, Cairo Road
    address = db.Column(db.Text)
    city = db.Column(db.String(80), index=True)
    phone = db.Column(db.String(30))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    coords_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Branch {self.name}>'
