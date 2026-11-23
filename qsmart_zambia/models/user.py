from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('ix_users_role_status', 'role', 'staff_status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    # Legacy plain-text OTP column kept for backward compatibility (no longer written)
    otp_code = db.Column(db.String(10))
    otp_expires = db.Column(db.DateTime)
    otp_channel = db.Column(db.String(10))  # sms | email
    # Secure OTP fields
    otp_hash = db.Column(db.String(128))
    otp_attempts = db.Column(db.Integer, default=0)
    otp_resend_at = db.Column(db.DateTime)
    # Password reset
    reset_token = db.Column(db.String(128))
    reset_token_expires = db.Column(db.DateTime)
    preferred_language = db.Column(db.String(20), default='en')
    role = db.Column(db.String(20), nullable=False, default='customer', index=True)
    # customer | staff | admin

    # Staff fields
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=True, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('institution_branches.id'), nullable=True)
    department = db.Column(db.String(100))
    staff_id_number = db.Column(db.String(50))
    staff_status = db.Column(db.String(20), index=True)  # pending | approved | rejected | suspended
    staff_role = db.Column(db.String(30), default='staff')
    # institution_admin | supervisor | receptionist | counter_staff | staff
    staff_note = db.Column(db.String(255))
    privacy_consent_at = db.Column(db.DateTime)
    privacy_consent_version = db.Column(db.String(20))
    data_purpose = db.Column(db.String(80), default='queue_service')
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    is_active = db.Column(db.Boolean, default=True, index=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    institution = db.relationship('Institution', foreign_keys=[institution_id], backref=db.backref('staff_members', lazy='dynamic'))
    approved_by = db.relationship('User', foreign_keys=[approved_by_id], remote_side=[id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_verified(self):
        """True if either phone or email has been verified."""
        return bool(self.phone_verified or self.email_verified)

    @property
    def is_admin(self):
        active = True if self.is_active is None else bool(self.is_active)
        return self.role == 'admin' and active

    @property
    def is_staff(self):
        active = True if self.is_active is None else bool(self.is_active)
        if not active:
            return False
        if self.role == 'admin':
            return True
        return self.role == 'staff' and self.staff_status == 'approved'

    @property
    def is_pending_staff(self):
        return self.role == 'staff' and self.staff_status == 'pending'

    @property
    def is_customer(self):
        return self.role == 'customer' and (self.is_active is None or self.is_active)

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def record_failed_login(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        db.session.commit()

    def reset_failed_logins(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
