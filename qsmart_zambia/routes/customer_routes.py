from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.security import customer_required
from utils.database import db
from utils.helpers import make_ticket_number, make_query_ref
from utils.activity import log_activity
from utils.notifications import notify
from utils.sms import send_sms, refresh_queue_positions
from utils.prediction import estimate_wait_minutes, recommend_counter, pickup_prediction
from utils.email_util import send_email
from models.institution import Institution, InstitutionBranch
from models.service import Service
from models.queue import QueueTicket
from models.query import CustomerQuery, QueryMessage
from models.notification import Notification
from datetime import datetime
from flask import current_app
from utils.uploads import save_query_attachment

ZAMBIAN_LANGUAGES = [
    ('en', 'English'),
    ('bem', 'Bemba (Ichibemba)'),
    ('nya', 'Nyanja / Chewa (Chinyanja)'),
    ('toi', 'Tonga (Chitonga)'),
    ('loz', 'Lozi (Silozi)'),
    ('kqn', 'Kaonde'),
    ('lue', 'Luvale'),
    ('lun', 'Lunda'),
]

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    q = Institution.query.filter_by(is_active=True)
    city = request.args.get('city', '').strip()
    category = request.args.get('category', '').strip()
    search = request.args.get('q', '').strip()
    if city:
        # filter by branch city
        branch_ids = [b.institution_id for b in InstitutionBranch.query.filter(
            InstitutionBranch.city.ilike(f'%{city}%'), InstitutionBranch.is_active == True
        ).all()]
        q = q.filter(Institution.id.in_(branch_ids or [0]))
    if category:
        q = q.filter_by(category=category)
    if search:
        q = q.filter(Institution.name.ilike(f'%{search}%'))
    institutions = q.order_by(Institution.name).all()

    tickets = QueueTicket.query.filter(
        QueueTicket.user_id == current_user.id,
        QueueTicket.status.in_(['waiting', 'called', 'serving'])
    ).order_by(QueueTicket.joined_at.desc()).all()

    queries = CustomerQuery.query.filter_by(user_id=current_user.id).order_by(
        CustomerQuery.created_at.desc()
    ).limit(20).all()

    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(15).all()

    map_points = []
    for inst in institutions:
        for b in inst.branches.filter_by(is_active=True):
            if b.latitude and b.longitude:
                map_points.append({
                    'name': inst.name, 'branch': b.name, 'lat': b.latitude, 'lng': b.longitude,
                    'category': inst.category, 'city': b.city or '', 'id': inst.id,
                })

    cities = sorted({b.city for b in InstitutionBranch.query.filter_by(is_active=True).all() if b.city})
    return render_template(
        'customer/dashboard.html',
        institutions=institutions, tickets=tickets, queries=queries,
        notifications=notifications, map_points=map_points, cities=cities,
        selected_city=city, selected_category=category, search=search,
    )


@customer_bp.route('/join-queue', methods=['GET', 'POST'])
@login_required
@customer_required
def join_queue():
    institutions = Institution.query.filter_by(is_active=True).order_by(Institution.name).all()
    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)
        service = db.session.get(Service, service_id)
        if not service or not service.is_active:
            flash('Select a valid service.', 'error')
            return redirect(url_for('customer.join_queue'))

        existing = QueueTicket.query.filter_by(
            user_id=current_user.id, service_id=service.id, status='waiting'
        ).first()
        if existing:
            flash(f'You already have ticket {existing.ticket_number} for this service.', 'info')
            return redirect(url_for('customer.ticket', ticket_number=existing.ticket_number))

        waiting = QueueTicket.query.filter_by(service_id=service.id, status='waiting').count()
        position = waiting + 1
        ticket = QueueTicket(
            ticket_number=make_ticket_number(),
            user_id=current_user.id,
            service_id=service.id,
            institution_id=service.institution_id,
            branch_id=service.branch_id,
            status='waiting',
            position=position,
            estimated_wait=position * (service.avg_service_time or 10),
        )
        ticket.estimated_wait = estimate_wait_minutes(service, position)
        rec_counter, rec_reason = recommend_counter(service)
        db.session.add(ticket)
        db.session.commit()
        log_activity('join_queue', user=current_user, detail=ticket.ticket_number)
        tip = pickup_prediction(ticket)
        notify(current_user.id, 'Queue joined',
               f'Ticket {ticket.ticket_number} — position {position}. {tip}',
               link=url_for('customer.ticket', ticket_number=ticket.ticket_number),
               category='queue')
        # SMS + email status
        body = (f'QSMART: Ticket {ticket.ticket_number} at {service.institution.name}. '
                f'Position #{position}, est. wait ~{ticket.estimated_wait} min. {tip}')
        if current_user.phone:
            send_sms(current_user.phone, body[:160], message_type='queue_join', related_ref=ticket.ticket_number)
        if current_user.email:
            send_email(current_user.email, f'QSMART ticket {ticket.ticket_number}', body)
        flash(f'Ticket {ticket.ticket_number} issued. Position #{position}. {rec_reason}', 'success')
        return redirect(url_for('customer.ticket', ticket_number=ticket.ticket_number))

    return render_template('customer/join_queue.html', institutions=institutions)


@customer_bp.route('/ticket/<ticket_number>')
@login_required
@customer_required
def ticket(ticket_number):
    t = QueueTicket.query.filter_by(ticket_number=ticket_number, user_id=current_user.id).first_or_404()
    tip = pickup_prediction(t)
    return render_template('customer/ticket.html', ticket=t, pickup_tip=tip)


@customer_bp.route('/ticket/<ticket_number>/cancel', methods=['POST'])
@login_required
@customer_required
def cancel_ticket(ticket_number):
    t = QueueTicket.query.filter_by(ticket_number=ticket_number, user_id=current_user.id).first_or_404()
    if t.status == 'waiting':
        sid = t.service_id
        t.status = 'cancelled'
        db.session.commit()
        refresh_queue_positions(sid)
        flash('Ticket cancelled.', 'info')
    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/query', methods=['GET', 'POST'])
@login_required
@customer_required
def send_query():
    institutions = Institution.query.filter_by(is_active=True).order_by(Institution.name).all()
    if request.method == 'POST':
        institution_id = request.form.get('institution_id', type=int)
        subject = request.form.get('subject', '').strip()[:150]
        message = request.form.get('message', '').strip()
        language = request.form.get('language', 'en')
        voice_blob = request.files.get('voice_note')
        attach_file = request.files.get('attachment')

        if language not in {c for c, _ in ZAMBIAN_LANGUAGES}:
            language = 'en'
        if not institution_id:
            flash('Select an institution.', 'error')
            return redirect(url_for('customer.send_query'))

        has_text = bool(message and len(message.strip()) >= 2)
        has_voice = bool(voice_blob and voice_blob.filename)
        has_file = bool(attach_file and attach_file.filename)
        if not has_text and not has_voice and not has_file:
            flash('Write a message, record a voice note, or attach a photo/document.', 'error')
            return redirect(url_for('customer.send_query'))

        voice_path = attachment_path = attachment_name = attachment_type = None
        for fs in (voice_blob, attach_file):
            if not fs or not fs.filename:
                continue
            result = save_query_attachment(fs, current_user.id, ref_prefix='q')
            if not result:
                continue
            if result.get('error'):
                flash(result['error'], 'error')
                return redirect(url_for('customer.send_query'))
            if result['type'] == 'voice':
                voice_path = result['path']
            else:
                attachment_path = result['path']
                attachment_name = result['name']
                attachment_type = result['type']

        q = CustomerQuery(
            reference=make_query_ref(),
            user_id=current_user.id,
            institution_id=institution_id,
            subject=subject or 'General enquiry',
            language=language,
            status='new',
        )
        db.session.add(q)
        db.session.flush()
        body_text = (message or '').strip()
        if not body_text:
            body_text = '[Voice note]' if voice_path else ('[Photo]' if attachment_type == 'image' else '[Attachment]')
        db.session.add(QueryMessage(
            query_id=q.id, sender_id=current_user.id,
            body=body_text, voice_path=voice_path,
            attachment_path=attachment_path, attachment_name=attachment_name,
            attachment_type=attachment_type, is_staff=False,
        ))
        db.session.commit()

        # Notify staff of that institution
        from models.user import User
        staff_list = User.query.filter_by(
            role='staff', staff_status='approved', institution_id=institution_id, is_active=True
        ).all()
        for s in staff_list:
            notify(s.id, 'New customer query',
                   f'{q.reference}: {q.subject}',
                   link=url_for('staff.query_detail', ref=q.reference),
                   category='query')

        log_activity('query_submit', user=current_user, detail=q.reference)
        flash(f'Query {q.reference} submitted. Staff will respond on your dashboard.', 'success')
        return redirect(url_for('customer.my_queries'))

    return render_template('customer/send_query.html', institutions=institutions, languages=ZAMBIAN_LANGUAGES)


@customer_bp.route('/queries')
@login_required
@customer_required
def my_queries():
    queries = CustomerQuery.query.filter_by(user_id=current_user.id).order_by(
        CustomerQuery.created_at.desc()
    ).all()
    return render_template('customer/my_queries.html', queries=queries)


@customer_bp.route('/queries/<ref>', methods=['GET', 'POST'])
@login_required
@customer_required
def query_detail(ref):
    q = CustomerQuery.query.filter_by(reference=ref, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        body = request.form.get('message', '').strip()
        voice_blob = request.files.get('voice_note')
        attach_file = request.files.get('attachment')
        voice_path = attachment_path = attachment_name = attachment_type = None
        for fs in (voice_blob, attach_file):
            if fs and fs.filename:
                result = save_query_attachment(fs, current_user.id, ref_prefix='r')
                if result and not result.get('error'):
                    if result['type'] == 'voice':
                        voice_path = result['path']
                    else:
                        attachment_path = result['path']
                        attachment_name = result['name']
                        attachment_type = result['type']
                elif result and result.get('error'):
                    flash(result['error'], 'error')
                    return redirect(url_for('customer.query_detail', ref=ref))
        if body or voice_path or attachment_path:
            if not body:
                body = '[Voice note]' if voice_path else ('[Photo]' if attachment_type == 'image' else '[Attachment]')
            db.session.add(QueryMessage(
                query_id=q.id, sender_id=current_user.id, body=body, is_staff=False,
                voice_path=voice_path, attachment_path=attachment_path,
                attachment_name=attachment_name, attachment_type=attachment_type,
            ))
            q.status = 'in_progress'
            q.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Reply sent.', 'success')
        return redirect(url_for('customer.query_detail', ref=ref))
    messages = q.messages.order_by(QueryMessage.created_at.asc()).all()
    return render_template('customer/query_detail.html', query=q, messages=messages)


@customer_bp.route('/notifications')
@login_required
@customer_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('customer/notifications.html', notifications=items)
