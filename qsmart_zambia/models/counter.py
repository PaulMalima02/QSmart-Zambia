from utils.database import db


class Counter(db.Model):
    __tablename__ = 'counters'

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    is_open = db.Column(db.Boolean, default=False, index=True)
    current_ticket = db.Column(db.String(20))

    def __repr__(self):
        return f'<Counter {self.name}>'
