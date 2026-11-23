from datetime import datetime, timedelta
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
from models.institution import Institution
from utils.database import db
from utils.helpers import EMAIL_RE, validate_password, validate_username, validate_full_name, validate_phone
from utils.activity import log_activity
from utils.notifications import notify

auth_bp = Blueprint('auth', __name__)


def _login_rate_ok(key='login_attempts', limit=8):
    attempts = session.get(key, 0)
    if attempts >= limit:
        flash('Too many attempts. Please wait and try again.', 'error')
        return False
    return True


def _redirect_for_role(user):
    if user.is_admin:
        return redirect(url_for('admin.dashboard'))
    if user.is_staff:
        return redirect(url_for('staff.dashboard'))
    if user.is_pending_staff:
        return redirect(url_for('auth.pending'))
    return redirect(url_for('customer.dashboard'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_for_role(current_user)

    role_hint = request.args.get('role', request.form.get('role', 'customer'))
    if role_hint not in ('customer', 'staff', 'admin'):
        role_hint = 'customer'

    unverified = request.args.get('unverified') == '1'

    if request.method == 'POST':
        if not _login_rate_ok():
            return render_template('auth/login.html', role=role_hint, unverified=False)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', 'customer')

        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        if not user or not user.check_password(password):
            session['login_attempts'] = session.get('login_attempts', 0) + 1
            if user:
                user.record_failed_login(
                    current_app.config.get('MAX_LOGIN_ATTEMPTS', 5),
                    current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15),
                )
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        # Role must match account — never elevate by selecting Admin in the form
        if selected_role == 'admin' and user.role != 'admin':
            flash('This account is not an administrator.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)
        if selected_role == 'staff' and user.role not in ('staff', 'admin'):
            flash('This account is not a staff account. Use Customer login.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)
        if selected_role == 'customer' and user.role != 'customer':
            flash('Staff and admin accounts must use Staff or Admin login.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        if not user.is_active:
            flash('This account has been deactivated.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        if user.is_locked():
            flash('Account temporarily locked. Try again later.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        if user.role == 'staff' and user.staff_status == 'pending':
            user.reset_failed_logins()
            session.pop('login_attempts', None)
            login_user(user)
            # Still require verification
            if not (user.phone_verified or user.email_verified):
                flash('Please verify your account first.', 'warning')
                return redirect(url_for('auth.verify'))
            return redirect(url_for('auth.pending'))

        if user.role == 'staff' and user.staff_status == 'rejected':
            flash('Your staff application was rejected. Contact the administrator.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        if user.role == 'staff' and user.staff_status == 'suspended':
            flash('Your staff account is suspended.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        if user.role == 'staff' and user.staff_status != 'approved':
            flash('Staff access is not authorised.', 'error')
            return render_template('auth/login.html', role=selected_role, unverified=False)

        user.reset_failed_logins()
        session.pop('login_attempts', None)
        login_user(user, remember=bool(request.form.get('remember')))
        try:
            log_activity('login', user=user, detail=f'role={user.role}')
        except Exception:
            pass

        # Enforce verification after successful login (admins bypass)
        if not user.is_admin and not (user.phone_verified or user.email_verified):
            flash('Please verify your account to continue.', 'warning')
            return redirect(url_for('auth.verify'))

        flash(f'Welcome, {user.full_name or user.username}!', 'success')
        return _redirect_for_role(user)

    return render_template('auth/login.html', role=role_hint, unverified=unverified)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer or staff registration only — never creates admin."""
    if current_user.is_authenticated:
        return _redirect_for_role(current_user)

    role = request.args.get('role', request.form.get('role', 'customer'))
    if role not in ('customer', 'staff'):
        role = 'customer'  # force — admin cannot public-register

    institutions = Institution.query.filter_by(is_active=True).order_by(Institution.name).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()[:120]
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '')  # validated below
        address = request.form.get('address', '').strip()[:255]
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'customer')
        channel = request.form.get('verify_channel', 'sms')
        if channel not in ('sms', 'email'):
            channel = 'sms'
        if role not in ('customer', 'staff'):
            role = 'customer'

        errors = []
        # Full name must be a string (letters)
        fn_err = validate_full_name(full_name)
        if fn_err:
            errors.append(fn_err)
        else:
            full_name = full_name.strip()

        # Username must be a string (not pure numbers)
        un_err = validate_username(username)
        if un_err:
            errors.append(un_err)
        else:
            username = username.strip()

        if not EMAIL_RE.match(email):
            errors.append('Valid email required.')

        pe = validate_password(password, current_app.config.get('MIN_PASSWORD_LENGTH', 8))
        if pe:
            errors.append(pe)
        if password != confirm:
            errors.append('Passwords do not match.')

        if not un_err and User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')

        # Phone must be digits only (normalized to +260…)
        phone_err, phone = validate_phone(request.form.get('phone', ''))
        if phone_err:
            errors.append(phone_err)

        if not request.form.get('privacy_consent'):
            errors.append('You must accept the privacy notice to create an account.')

        institution_id = None
        department = staff_id_number = None
        if role == 'staff':
            institution_id = request.form.get('institution_id', type=int)
            department = request.form.get('department', '').strip()[:100]
            staff_id_number = request.form.get('staff_id_number', '').strip()[:50]
            if not institution_id or not db.session.get(Institution, institution_id):
                errors.append('Select your institution.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('auth/register.html', role=role, institutions=institutions)

        user = User(
            username=username, email=email, full_name=full_name, phone=phone,
            address=address, role=role, is_active=True,
        )
        if role == 'staff':
            user.institution_id = institution_id
            user.department = department
            user.staff_id_number = staff_id_number
            user.staff_status = 'pending'
            user.staff_note = request.form.get('staff_note', '').strip()[:255]
        user.set_password(password)
        user.privacy_consent_at = datetime.utcnow()
        user.privacy_consent_version = current_app.config.get('PRIVACY_POLICY_VERSION', '1.0')
        user.data_purpose = 'queue_service'
        # staff sub-role from form
        if role == 'staff':
            sr = request.form.get('staff_role', 'staff')
            if sr in ('institution_admin', 'supervisor', 'receptionist', 'counter_staff', 'staff'):
                user.staff_role = sr
        db.session.add(user)
        db.session.commit()
        try:
            log_activity('register', user=user, detail=f'role={role}')
        except Exception:
            pass

        from utils.otp import issue_otp
        login_user(user)
        ok, msg = issue_otp(user, channel=channel)
        flash(msg or 'Account created. Enter the confirmation code.', 'info')
        if role == 'staff':
            flash('After verification, an admin must approve your staff access.', 'info')
        return redirect(url_for('auth.verify'))

    return render_template('auth/register.html', role=role, institutions=institutions)


@auth_bp.route('/pending')
@login_required
def pending():
    if current_user.is_staff or current_user.is_admin:
        return _redirect_for_role(current_user)
    if not current_user.is_pending_staff:
        return redirect(url_for('auth.login'))
    return render_template('auth/pending.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    try:
        if current_user.is_authenticated:
            try:
                log_activity('logout', user=current_user)
            except Exception:
                pass
            logout_user()
    except Exception:
        pass
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        # Always show the same message to avoid email enumeration
        flash(
            'If that email exists, password reset instructions will be sent. '
            'Check your inbox (or the on-screen code in development mode).',
            'info',
        )
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate secure reset token
            raw_token = secrets.token_urlsafe(32)
            expiry = current_app.config.get('RESET_TOKEN_EXPIRY_MINUTES', 15)
            user.reset_token = generate_password_hash(raw_token, method='scrypt')
            user.reset_token_expires = datetime.utcnow() + timedelta(minutes=expiry)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=raw_token, _external=True)
            subject = 'QSMART Zambia – Password Reset'
            text_body = (
                f'Hello {user.full_name or user.username},\n\n'
                f'You requested a password reset. Click the link below (valid {expiry} minutes):\n\n'
                f'{reset_url}\n\n'
                f'If you did not request this, ignore this email.\n'
            )
            html_body = f'''
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
              <h2 style="color:#0b1f3a">Password Reset</h2>
              <p>Hello {user.full_name or user.username},</p>
              <p>You requested a password reset for your QSMART Zambia account.</p>
              <p style="text-align:center;margin:24px 0">
                <a href="{reset_url}" style="background:#0d9488;color:#fff;padding:12px 24px;
                   border-radius:8px;text-decoration:none;font-weight:600">Reset Password</a>
              </p>
              <p style="color:#64748b;font-size:13px">Link expires in {expiry} minutes. If you did not request this, ignore this email.</p>
            </div>
            '''
            from utils.email_util import send_email
            ok, status = send_email(user.email, subject, text_body, html_body=html_body)
            if not ok:
                # Dev mode: expose token on-screen via session
                session['dev_reset_token'] = raw_token
                session['dev_reset_email'] = user.email
                flash(
                    f'Development mode: email not configured. Use this reset link: {reset_url}',
                    'warning',
                )
            try:
                log_activity('password_reset_request', user=user)
            except Exception:
                pass
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Find user whose hashed token matches
    user = None
    candidates = User.query.filter(
        User.reset_token.isnot(None),
        User.reset_token_expires.isnot(None),
    ).all()
    for u in candidates:
        if u.reset_token_expires and datetime.utcnow() > u.reset_token_expires:
            continue
        if u.reset_token and check_password_hash(u.reset_token, token):
            user = u
            break

    if not user:
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        pe = validate_password(password, current_app.config.get('MIN_PASSWORD_LENGTH', 8))
        if pe:
            flash(pe, 'error')
            return render_template('auth/reset_password.html', token=token)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expires = None
        # Clear any lockout
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        try:
            log_activity('password_reset', user=user)
        except Exception:
            pass
        session.pop('dev_reset_token', None)
        session.pop('dev_reset_email', None)
        flash('Password updated successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/verify-phone', methods=['GET', 'POST'])
@login_required
def verify_phone():
    """Legacy URL — redirect to /verify."""
    return redirect(url_for('auth.verify'), code=301)


@auth_bp.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    """Confirm account with OTP sent to the user's registered mobile or email."""
    if current_user.phone_verified or current_user.email_verified:
        flash('Account already verified.', 'success')
        return _redirect_for_role(current_user)

    from utils.otp import (
        issue_otp, verify_otp, get_onscreen_otp, can_resend,
        get_attempts_remaining, _sms_configured, _email_configured,
    )

    if request.method == 'POST':
        action = request.form.get('action', 'verify')
        if action in ('resend_sms', 'resend_email'):
            channel = 'sms' if action == 'resend_sms' else 'email'
            ok, msg = issue_otp(current_user, channel=channel)
            flash(msg, 'info' if ok else 'error')
            return redirect(url_for('auth.verify'))
        code = request.form.get('otp', '').strip()
        # Also accept individual digit fields
        if not code:
            digits = [request.form.get(f'd{i}', '') for i in range(1, 7)]
            code = ''.join(digits)
        ok, msg = verify_otp(current_user, code)
        if ok:
            flash(msg, 'success')
            if current_user.is_pending_staff:
                return redirect(url_for('auth.pending'))
            return _redirect_for_role(current_user)
        flash(msg, 'error')

    onscreen = get_onscreen_otp(current_user)
    allowed, remaining = can_resend(current_user)
    attempts_left = get_attempts_remaining(current_user)
    max_attempts = current_app.config.get('OTP_MAX_ATTEMPTS', 5)
    return render_template(
        'auth/verify.html',
        onscreen_code=onscreen,
        sms_ready=_sms_configured(),
        email_ready=_email_configured(),
        resend_allowed=allowed,
        resend_remaining=remaining,
        attempts_left=attempts_left,
        max_attempts=max_attempts,
        cooldown_seconds=current_app.config.get('OTP_RESEND_COOLDOWN_SECONDS', 60),
    )
