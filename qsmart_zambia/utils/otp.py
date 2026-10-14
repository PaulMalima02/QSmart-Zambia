"""Secure OTP generation, hashing, rate-limiting and verification."""
import secrets
from datetime import datetime, timedelta
from flask import current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database import db
from utils.sms import send_sms
from utils.email_util import send_email


def generate_otp():
    """Cryptographically secure 6-digit OTP."""
    return f'{secrets.randbelow(1_000_000):06d}'


def _sms_configured():
    provider = (current_app.config.get('SMS_PROVIDER') or 'log').lower()
    key = current_app.config.get('SMS_API_KEY') or ''
    return provider != 'log' and bool(key)


def _email_configured():
    """True if Resend or SMTP is configured."""
    provider = (current_app.config.get('EMAIL_PROVIDER') or '').lower()
    if provider == 'resend' and current_app.config.get('RESEND_API_KEY'):
        return True
    return bool(current_app.config.get('MAIL_SERVER'))


def can_resend(user):
    """
    Return (allowed: bool, remaining_seconds: int).
    remaining_seconds is 0 when allowed.
    """
    if not user.otp_resend_at:
        return True, 0
    now = datetime.utcnow()
    if now >= user.otp_resend_at:
        return True, 0
    remaining = int((user.otp_resend_at - now).total_seconds())
    return False, max(0, remaining)


def issue_otp(user, channel='sms'):
    """
    Issue a 6-digit OTP with hashing, expiry and resend cooldown.
    - If SMS/email is configured → send via provider
    - If not configured (typical local setup) → store code and expose it for on-screen display
    Returns (success: bool, message: str)
    """
    allowed, remaining = can_resend(user)
    if not allowed:
        return False, f'Please wait {remaining} second{"s" if remaining != 1 else ""} before requesting a new code.'

    code = generate_otp()
    expiry_min = current_app.config.get('OTP_EXPIRY_MINUTES', 5)
    cooldown = current_app.config.get('OTP_RESEND_COOLDOWN_SECONDS', 60)

    # Hash and store — never keep plain-text in DB
    user.otp_hash = generate_password_hash(code, method='scrypt')
    user.otp_code = None  # clear legacy plain-text
    user.otp_expires = datetime.utcnow() + timedelta(minutes=expiry_min)
    user.otp_channel = channel if channel in ('sms', 'email') else 'sms'
    user.otp_attempts = 0
    user.otp_resend_at = datetime.utcnow() + timedelta(seconds=cooldown)
    db.session.commit()

    # Short-lived session copy for on-screen display when delivery is offline
    session['dev_otp_hint'] = code
    session['dev_otp_user'] = user.id

    delivered = False
    messages = []
    msg_body = f'QSMART Zambia verification code: {code}. Valid {expiry_min} minutes.'

    if channel == 'sms' and user.phone:
        if _sms_configured():
            ok, status = send_sms(
                user.phone,
                msg_body,
                message_type='otp',
                related_ref=user.username,
            )
            delivered = ok
            messages.append('SMS sent to your phone.' if ok else f'SMS status: {status}.')
        else:
            send_sms(
                user.phone,
                msg_body,
                message_type='otp',
                related_ref=user.username,
            )
            messages.append(
                'SMS provider is not configured. Use the on-screen code below to verify.'
            )
    elif channel == 'email' and user.email:
        subject = 'QSMART Zambia verification code'
        text_body = (
            f'Your QSMART Zambia verification code is {code}.\n'
            f'It expires in {expiry_min} minutes.\n\n'
            f'If you did not request this, ignore this email.'
        )
        html_body = (
            '<div style="font-family:sans-serif;max-width:420px;margin:0 auto">'
            '<h2 style="color:#0b1f3a">Verification code</h2>'
            '<p>Your QSMART Zambia code is:</p>'
            f'<p style="font-size:28px;font-weight:700;letter-spacing:0.2em;text-align:center;'
            f'background:#f1f5f9;padding:16px;border-radius:8px">{code}</p>'
            f'<p style="color:#64748b;font-size:13px">Expires in {expiry_min} minutes.</p>'
            '</div>'
        )
        if _email_configured():
            ok, status = send_email(user.email, subject, text_body, html_body=html_body)
            delivered = ok
            messages.append('Email sent.' if ok else f'Email status: {status}.')
        else:
            send_email(user.email, subject, text_body, html_body=html_body)
            messages.append(
                'Email is not configured. Use the on-screen code below to verify.'
            )
    else:
        messages.append('No phone/email on file. Code is shown on screen for this session.')

    # Always printable in server console (dev convenience)
    print(f'[QSMART OTP] user={user.username} code={code} channel={channel}')

    return True, ' '.join(messages)


def verify_otp(user, code):
    """
    Verify OTP against hash, check expiry and attempt limits.
    On success: mark verified, clear OTP fields.
    Returns (success: bool, message: str)
    """
    max_attempts = current_app.config.get('OTP_MAX_ATTEMPTS', 5)

    if not user.otp_hash or not user.otp_expires:
        return False, 'No code requested. Tap Resend to get a new code.'

    if datetime.utcnow() > user.otp_expires:
        return False, 'Code expired. Request a new one.'

    attempts = user.otp_attempts or 0
    if attempts >= max_attempts:
        return False, f'Too many failed attempts ({max_attempts}). Request a new code.'

    if not check_password_hash(user.otp_hash, str(code).strip()):
        user.otp_attempts = attempts + 1
        db.session.commit()
        remaining = max_attempts - user.otp_attempts
        if remaining <= 0:
            return False, f'Too many failed attempts ({max_attempts}). Request a new code.'
        return False, f'Invalid code. {remaining} attempt{"s" if remaining != 1 else ""} remaining.'

    # Success — mark verified based on channel used
    channel = (user.otp_channel or 'sms').lower()
    if channel == 'email':
        user.email_verified = True
    else:
        user.phone_verified = True
        # Also mark email verified if present (single verification flow)
        if user.email:
            user.email_verified = True

    # Invalidate OTP
    user.otp_hash = None
    user.otp_code = None
    user.otp_expires = None
    user.otp_attempts = 0
    user.otp_resend_at = None
    db.session.commit()

    session.pop('dev_otp_hint', None)
    session.pop('dev_otp_user', None)
    return True, 'Account verified successfully.'


def get_onscreen_otp(user):
    """Return the current OTP for display when SMS/email is not configured."""
    if not user or not user.otp_hash:
        return None
    if user.otp_expires and datetime.utcnow() > user.otp_expires:
        return None
    # Prefer session hint matching this user
    if session.get('dev_otp_user') == user.id and session.get('dev_otp_hint'):
        return session.get('dev_otp_hint')
    # Fallback only when providers are offline
    if not _sms_configured() and not _email_configured():
        return session.get('dev_otp_hint') if session.get('dev_otp_user') == user.id else None
    return None


def get_attempts_remaining(user):
    """Return remaining verification attempts."""
    max_attempts = current_app.config.get('OTP_MAX_ATTEMPTS', 5)
    used = user.otp_attempts or 0
    return max(0, max_attempts - used)
