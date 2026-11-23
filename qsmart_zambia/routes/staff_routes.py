from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from utils.security import staff_required
from utils.database import db
from utils.activity import log_activity
from utils.notifications import notify
from utils.sms import send_sms, refresh_queue_positions, notify_queue_next
from utils.email_util import send_email
from models.queue import QueueTicket
from models.service import Service, Counter
from models.query import CustomerQuery, QueryMessage
from models.notification import Notification
from utils.uploads import save_query_attachment

staff_bp = Blueprint('staff', __name__)


def _inst_id():
    if current_user.is_admin:
        return request.args.get('institution_id', type=int) or current_user.institution_id
    return current_user.institution_id


@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    inst_id = _inst_id()
    svc_ids = [s.id for s in Service.query.filter_by(institution_id=inst_id, is_active=True).all()] if inst_id else []

    waiting = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'waiting'
    ).count() if svc_ids else 0
    serving = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status.in_(['called', 'serving'])
    ).count() if svc_ids else 0
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'completed',
        QueueTicket.completed_at >= today
    ).count() if svc_ids else 0

    open_queries = CustomerQuery.query.filter(
        CustomerQuery.institution_id == inst_id,
        CustomerQuery.status.in_(['new', 'assigned', 'in_progress', 'replied'])
    ).order_by(CustomerQuery.created_at.desc()).limit(10).all() if inst_id else []

    next_waiting = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'waiting'
    ).order_by(QueueTicket.joined_at.asc()).limit(8).all() if svc_ids else []

    return render_template(
        'staff/dashboard.html',
        waiting=waiting, serving=serving, completed=completed,
        open_queries=open_queries, next_waiting=next_waiting,
    )


@staff_bp.route('/queue', methods=['GET', 'POST'])
@login_required
@staff_required
def queue_manage():
    inst_id = current_user.institution_id if not current_user.is_admin else _inst_id()
    if not inst_id and not current_user.is_admin:
        flash('No institution assigned.', 'error')
        return redirect(url_for('staff.dashboard'))

    svc_ids = [s.id for s in Service.query.filter_by(institution_id=inst_id).all()] if inst_id else []
    waiting = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'waiting'
    ).order_by(QueueTicket.joined_at.asc()).all() if svc_ids else []
    serving = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status.in_(['called', 'serving'])
    ).all() if svc_ids else []
    counters = Counter.query.filter_by(institution_id=inst_id, is_open=True).all() if inst_id else []

    if request.method == 'POST':
        action = request.form.get('action')
        ticket_id = request.form.get('ticket_id', type=int)
        t = db.session.get(QueueTicket, ticket_id)
        if not t or (not current_user.is_admin and t.institution_id != current_user.institution_id):
            flash('Ticket not found or not allowed.', 'error')
            return redirect(url_for('staff.queue_manage'))

        if action == 'call':
            counter_id = request.form.get('counter_id', type=int)
            counter = db.session.get(Counter, counter_id) if counter_id else None
            if t.status != 'waiting':
                flash('Ticket is not waiting.', 'error')
            else:
                t.status = 'called'
                t.called_at = datetime.utcnow()
                if counter:
                    t.counter_id = counter.id
                    counter.current_ticket = t.ticket_number
                db.session.commit()
                refresh_queue_positions(t.service_id)
                notify_queue_next(t, counter.name if counter else None)
                log_activity('call_ticket', user=current_user, detail=t.ticket_number)
                flash(f'Called {t.ticket_number}. Customer notified.', 'success')

        elif action == 'serve':
            if t.status in ('called', 'waiting'):
                t.status = 'serving'
                t.started_at = datetime.utcnow()
                db.session.commit()
                flash(f'{t.ticket_number} is now being served.', 'success')

        elif action == 'complete':
            sid = t.service_id
            counter_name = t.counter.name if t.counter else None
            t.status = 'completed'
            t.completed_at = datetime.utcnow()
            if t.counter:
                t.counter.current_ticket = None
            db.session.commit()
            refresh_queue_positions(sid)
            # Notify who is now first
            nxt = QueueTicket.query.filter_by(service_id=sid, status='waiting').order_by(
                QueueTicket.joined_at.asc()
            ).first()
            if nxt:
                nxt.position = 1
                db.session.commit()
                notify_queue_next(nxt, counter_name)
            log_activity('complete_ticket', user=current_user, detail=t.ticket_number)
            flash(f'{t.ticket_number} completed. Next customer notified if waiting.', 'success')

        elif action == 'skip':
            sid = t.service_id
            t.status = 'skipped'
            if t.counter:
                t.counter.current_ticket = None
            db.session.commit()
            refresh_queue_positions(sid)
            flash(f'{t.ticket_number} skipped.', 'info')

        return redirect(url_for('staff.queue_manage'))

    return render_template(
        'staff/queue_management.html', waiting=waiting, serving=serving, counters=counters
    )


@staff_bp.route('/queries')
@login_required
@staff_required
def queries():
    inst_id = current_user.institution_id
    if current_user.is_admin:
        q = CustomerQuery.query
    else:
        q = CustomerQuery.query.filter_by(institution_id=inst_id)
    status = request.args.get('status', '')
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(CustomerQuery.created_at.desc()).limit(100).all()
    return render_template('staff/queries.html', queries=items, status=status)


@staff_bp.route('/queries/<ref>', methods=['GET', 'POST'])
@login_required
@staff_required
def query_detail(ref):
    q = CustomerQuery.query.filter_by(reference=ref).first_or_404()
    if not current_user.is_admin and q.institution_id != current_user.institution_id:
        flash('Not authorised for this query.', 'error')
        return redirect(url_for('staff.queries'))

    if request.method == 'POST':
        body = request.form.get('message', '').strip()
        action = request.form.get('action', 'reply')
        voice_blob = request.files.get('voice_note')
        attach_file = request.files.get('attachment')
        voice_path = attachment_path = attachment_name = attachment_type = None
        for fs in (voice_blob, attach_file):
            if fs and fs.filename:
                result = save_query_attachment(fs, current_user.id, ref_prefix='s')
                if result and not result.get('error'):
                    if result['type'] == 'voice':
                        voice_path = result['path']
                    else:
                        attachment_path = result['path']
                        attachment_name = result['name']
                        attachment_type = result['type']
        if body or voice_path or attachment_path:
            if not body:
                body = '[Voice note]' if voice_path else ('[Photo]' if attachment_type == 'image' else '[Attachment]')
            db.session.add(QueryMessage(
                query_id=q.id, sender_id=current_user.id, body=body, is_staff=True,
                voice_path=voice_path, attachment_path=attachment_path,
                attachment_name=attachment_name, attachment_type=attachment_type,
            ))
            q.assigned_staff_id = current_user.id
            q.status = 'replied'
            q.updated_at = datetime.utcnow()
            db.session.commit()
            # In-app + SMS (short, no sensitive body)
            notify(
                q.user_id, 'Reply to your query',
                f'{q.reference}: Staff responded. Log in to read the full message.',
                link=url_for('customer.query_detail', ref=q.reference),
                category='query',
            )
            if q.user and q.user.phone:
                ok, st = send_sms(
                    q.user.phone,
                    f'QSMART: Reply to {q.reference}. Please log in to view the full response.',
                    message_type='query_reply',
                    related_ref=q.reference,
                )
            if q.user and q.user.email:
                send_email(
                    q.user.email,
                    f'QSMART reply to {q.reference}',
                    f'Staff responded to your query {q.reference}. Log in to QSMART Zambia to read the full message.',
                )
                if st == 'log_only':
                    flash('Reply saved. Customer notified in-app (SMS not configured).', 'success')
                elif ok:
                    flash('Reply saved. Customer notified in-app and by SMS.', 'success')
                else:
                    flash('Reply saved. Customer notified in-app (SMS failed — see SMS log).', 'success')
            else:
                flash('Reply saved. Customer notified in-app.', 'success')

        if action == 'resolve':
            q.status = 'resolved'
            q.resolved_at = datetime.utcnow()
            db.session.commit()
            flash('Query marked resolved.', 'success')
        elif action == 'close':
            q.status = 'closed'
            db.session.commit()
            flash('Query closed.', 'success')

        return redirect(url_for('staff.query_detail', ref=ref))

    messages = q.messages.order_by(QueryMessage.created_at.asc()).all()
    return render_template('staff/query_detail.html', query=q, messages=messages)


@staff_bp.route('/display')
@login_required
@staff_required
def public_display():
    """Public-facing board: ticket numbers only — never customer names (privacy)."""
    inst_id = current_user.institution_id
    if current_user.is_admin:
        inst_id = request.args.get('institution_id', type=int) or inst_id
    svc_ids = [s.id for s in Service.query.filter_by(institution_id=inst_id).all()] if inst_id else []
    waiting = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'waiting'
    ).order_by(QueueTicket.joined_at.asc()).limit(20).all() if svc_ids else []
    serving = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status.in_(['called', 'serving'])
    ).all() if svc_ids else []
    return render_template('staff/public_display.html', waiting=waiting, serving=serving)
