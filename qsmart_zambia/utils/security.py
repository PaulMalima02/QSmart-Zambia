from functools import wraps
from flask import abort, flash, redirect, url_for, session, request
from flask_login import current_user
from utils.permissions import user_can
from utils.activity import log_activity


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and not current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not user_can(current_user, permission):
                try:
                    log_activity('access_denied', user=current_user,
                                 detail=f'perm={permission} path={request.path}')
                except Exception:
                    pass
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Administrator access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped


def verification_required(f):
    """Redirect unverified users to the verification page.
    Admins and already-verified accounts pass through.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        # Admins are always considered verified
        if current_user.is_admin:
            return f(*args, **kwargs)
        if not (current_user.phone_verified or current_user.email_verified):
            flash('Please verify your account to continue.', 'warning')
            return redirect(url_for('auth.verify'))
        return f(*args, **kwargs)
    return wrapped


def staff_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_pending_staff:
            return redirect(url_for('auth.pending'))
        if not current_user.is_staff:
            flash('Staff access required.', 'error')
            return redirect(url_for('auth.login'))
        # Enforce verification for staff (except pending which already redirected)
        if not current_user.is_admin and not (current_user.phone_verified or current_user.email_verified):
            flash('Please verify your account to continue.', 'warning')
            return redirect(url_for('auth.verify'))
        return f(*args, **kwargs)
    return wrapped


def customer_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_admin or current_user.is_staff:
            return redirect(url_for('admin.dashboard') if current_user.is_admin else url_for('staff.dashboard'))
        # Enforce verification for customers
        if not (current_user.phone_verified or current_user.email_verified):
            flash('Please verify your account to continue.', 'warning')
            return redirect(url_for('auth.verify'))
        return f(*args, **kwargs)
    return wrapped


def touch_session_activity():
    """Update last activity timestamp for idle timeout on shared devices."""
    from datetime import datetime
    session['last_activity'] = datetime.utcnow().isoformat()
    session.permanent = True
