from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from utils.security import admin_required
from utils.database import db
from utils.activity import log_activity
from utils.notifications import notify
from utils.sms import send_sms
from models.user import User
from models.institution import Institution, InstitutionBranch
from models.service import Service, Counter
from models.queue import QueueTicket
from models.query import CustomerQuery
from models.notification import AuditLog, SmsLog

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'customers': User.query.filter_by(role='customer').count(),
        'staff_approved': User.query.filter_by(role='staff', staff_status='approved').count(),
        'pending_staff': User.query.filter_by(role='staff', staff_status='pending').count(),
        'institutions': Institution.query.filter_by(is_active=True).count(),
        'waiting': QueueTicket.query.filter_by(status='waiting').count(),
        'serving': QueueTicket.query.filter(QueueTicket.status.in_(['called', 'serving'])).count(),
        'completed_today': QueueTicket.query.filter(
            QueueTicket.status == 'completed', QueueTicket.completed_at >= today
        ).count(),
        'open_queries': CustomerQuery.query.filter(
            CustomerQuery.status.in_(['new', 'assigned', 'in_progress', 'replied'])
        ).count(),
        'admins': User.query.filter_by(role='admin').count(),
    }
    pending = User.query.filter_by(role='staff', staff_status='pending').order_by(
        User.created_at.desc()
    ).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, pending=pending)


@admin_bp.route('/staff')
@login_required
@admin_required
def staff_list():
    status = request.args.get('status', 'pending')
    q = User.query.filter_by(role='staff')
    if status in ('pending', 'approved', 'rejected', 'suspended'):
        q = q.filter_by(staff_status=status)
    staff_users = q.order_by(User.created_at.desc()).all()
    return render_template('admin/staff.html', staff_users=staff_users, status=status)


@admin_bp.route('/staff/<int:uid>/approve', methods=['POST'])
@login_required
@admin_required
def staff_approve(uid):
    user = db.session.get(User, uid)
    if not user or user.role != 'staff':
        flash('Not a staff application.', 'error')
        return redirect(url_for('admin.staff_list'))
    user.staff_status = 'approved'
    user.approved_at = datetime.utcnow()
    user.approved_by_id = current_user.id
    user.is_active = True
    # Optional reassignment
    inst_id = request.form.get('institution_id', type=int)
    if inst_id:
        user.institution_id = inst_id
    db.session.commit()
    notify(user.id, 'Staff approved',
           'Your staff account has been approved. You can log in and manage queues.',
           category='account')
    if user.phone:
        send_sms(user.phone, 'QSMART: Your staff account was approved. You may log in now.',
                 message_type='approval', related_ref=user.username)
    log_activity('staff_approved', user=current_user, detail=user.username)
    flash(f'Approved {user.full_name or user.username}.', 'success')
    return redirect(url_for('admin.staff_list', status='pending'))


@admin_bp.route('/staff/<int:uid>/reject', methods=['POST'])
@login_required
@admin_required
def staff_reject(uid):
    user = db.session.get(User, uid)
    if not user or user.role != 'staff':
        flash('Not a staff application.', 'error')
        return redirect(url_for('admin.staff_list'))
    reason = request.form.get('reason', '').strip()[:200]
    user.staff_status = 'rejected'
    user.staff_note = (user.staff_note or '') + (f' | Rejected: {reason}' if reason else ' | Rejected')
    db.session.commit()
    notify(user.id, 'Staff application rejected', reason or 'Contact the administrator.', category='account')
    log_activity('staff_rejected', user=current_user, detail=user.username)
    flash('Application rejected.', 'info')
    return redirect(url_for('admin.staff_list', status='pending'))


@admin_bp.route('/staff/<int:uid>/suspend', methods=['POST'])
@login_required
@admin_required
def staff_suspend(uid):
    user = db.session.get(User, uid)
    if user and user.role == 'staff':
        user.staff_status = 'suspended'
        user.is_active = False
        db.session.commit()
        log_activity('staff_suspended', user=current_user, detail=user.username)
        flash('Staff suspended.', 'info')
    return redirect(url_for('admin.staff_list', status='approved'))


@admin_bp.route('/institutions', methods=['GET', 'POST'])
@login_required
@admin_required
def institutions():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        category = request.form.get('category', 'government')
        if name and code and not Institution.query.filter_by(code=code).first():
            inst = Institution(name=name, code=code, category=category, is_active=True)
            db.session.add(inst)
            db.session.flush()
            branch_name = request.form.get('branch_name', 'Main').strip() or 'Main'
            db.session.add(InstitutionBranch(
                institution_id=inst.id, name=branch_name,
                address=request.form.get('address', ''),
                city=request.form.get('city', 'Lusaka'),
                latitude=request.form.get('latitude', type=float),
                longitude=request.form.get('longitude', type=float),
                is_active=True,
            ))
            db.session.commit()
            flash(f'Added {name}.', 'success')
        else:
            flash('Name and unique code required.', 'error')
        return redirect(url_for('admin.institutions'))

    items = Institution.query.order_by(Institution.name).all()
    return render_template('admin/institutions.html', institutions=items)


@admin_bp.route('/institutions/<int:iid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_institution(iid):
    inst = db.session.get(Institution, iid)
    if inst:
        inst.is_active = not inst.is_active
        db.session.commit()
    return redirect(url_for('admin.institutions'))


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=7)
    month = today - timedelta(days=30)
    summary = {
        'completed_today': QueueTicket.query.filter(
            QueueTicket.status == 'completed', QueueTicket.completed_at >= today
        ).count(),
        'completed_week': QueueTicket.query.filter(
            QueueTicket.status == 'completed', QueueTicket.completed_at >= week
        ).count(),
        'completed_month': QueueTicket.query.filter(
            QueueTicket.status == 'completed', QueueTicket.completed_at >= month
        ).count(),
        'queries_week': CustomerQuery.query.filter(CustomerQuery.created_at >= week).count(),
        'sms_sent': SmsLog.query.filter(SmsLog.status == 'sent').count(),
        'sms_failed': SmsLog.query.filter(SmsLog.status == 'failed').count(),
        'sms_log_only': SmsLog.query.filter(SmsLog.status == 'log_only').count(),
    }
    by_inst = db.session.query(
        Institution.name, db.func.count(QueueTicket.id)
    ).join(QueueTicket, QueueTicket.institution_id == Institution.id).filter(
        QueueTicket.status == 'completed', QueueTicket.completed_at >= week
    ).group_by(Institution.name).all()

    audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/reports.html', summary=summary, by_inst=by_inst, audits=audits)


@admin_bp.route('/customers')
@login_required
@admin_required
def customers():
    users = User.query.filter_by(role='customer').order_by(User.created_at.desc()).limit(100).all()
    return render_template('admin/customers.html', customers=users)


@admin_bp.route('/admins/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_admin():
    """Create additional admin up to MAX_ADMIN_ACCOUNTS (default 2)."""
    max_n = current_app.config.get('MAX_ADMIN_ACCOUNTS', 2)
    count = User.query.filter_by(role='admin').count()
    slots = max(0, max_n - count)
    if request.method == 'POST':
        if slots <= 0:
            flash(f'Maximum of {max_n} administrators reached.', 'error')
            return redirect(url_for('admin.dashboard'))
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        from utils.helpers import USERNAME_RE, EMAIL_RE, validate_password
        if not USERNAME_RE.match(username) or not EMAIL_RE.match(email):
            flash('Valid username and email required.', 'error')
            return redirect(url_for('admin.create_admin'))
        if validate_password(password):
            flash(validate_password(password), 'error')
            return redirect(url_for('admin.create_admin'))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'error')
            return redirect(url_for('admin.create_admin'))
        u = User(username=username, email=email, full_name=request.form.get('full_name', username),
                 role='admin', staff_status='approved', is_active=True, email_verified=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        log_activity('admin_created', user=current_user, detail=username)
        flash(f'Administrator {username} created.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/create_admin.html', slots=slots, max_n=max_n)
