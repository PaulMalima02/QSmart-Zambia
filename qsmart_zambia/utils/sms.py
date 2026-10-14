"""SMS service — local log gateway, Africa's Talking, Twilio.

Local gateway (default):
  SMS_PROVIDER=log  → messages are printed and stored in sms_log; never claimed as delivered.
  OTP codes also appear on the verify page and in the terminal.

Live providers:
  SMS_PROVIDER=africastalking  + SMS_API_KEY + SMS_USERNAME
  SMS_PROVIDER=twilio          + SMS_API_KEY=SID:TOKEN + SMS_FROM_NUMBER
"""
from flask import current_app
from utils.database import db


def send_sms(phone, message, message_type='general', related_ref=None):
    """
    Send (or log) an SMS.
    Returns (ok: bool, status: str) where status is log_only | sent | failed | no_phone.
    """
    if not phone:
        return False, 'no_phone'

    phone = str(phone).strip()
    provider = (current_app.config.get('SMS_PROVIDER') or 'log').lower().strip()
    api_key = (current_app.config.get('SMS_API_KEY') or '').strip()
    sender = current_app.config.get('SMS_SENDER', 'QSMART')

    status = 'log_only'
    provider_response = ''
    ok = False

    # Always print for local debugging
    print(f'[SMS:{provider}] To:{phone} Type:{message_type} Msg:{message[:120]}')

    if provider in ('log', '', 'none') or not api_key:
        status = 'log_only'
        provider_response = 'Local gateway: SMS credentials not configured; message logged only.'
        ok = False
    else:
        try:
            if provider == 'africastalking':
                provider_response = _africastalking(phone, message, sender, api_key)
                ok = _at_success(provider_response)
            elif provider == 'twilio':
                provider_response = _twilio(phone, message, sender, api_key)
                ok = _twilio_success(provider_response)
            else:
                provider_response = f'Unknown SMS_PROVIDER "{provider}". Use log, africastalking, or twilio.'
                ok = False
            status = 'sent' if ok else 'failed'
        except Exception as exc:
            status = 'failed'
            provider_response = str(exc)
            ok = False
            print(f'[SMS ERROR] {exc}')

    # Persist to sms_log for admin reports / debugging
    try:
        from models.notification import SmsLog
        log = SmsLog(
            phone=phone,
            message=message,
            message_type=message_type,
            related_ref=related_ref,
            status=status,
            provider_response=(provider_response or '')[:500] or None,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print('sms log error:', e)

    return ok, status


def _at_success(response):
    """Heuristic: Africa's Talking success indicators."""
    if not response:
        return False
    r = response.lower()
    return (
        'success' in r
        or '"statuscode":"101"' in r.replace(' ', '')
        or 'smsmessagedata' in r
        or '"status":"success"' in r
    )


def _twilio_success(response):
    """Heuristic: Twilio success indicators."""
    if not response:
        return False
    return '"sid"' in response or '"status"' in response


def _africastalking(phone, message, sender, api_key):
    import urllib.request
    import urllib.parse

    username = current_app.config.get('SMS_USERNAME', 'sandbox')
    data = urllib.parse.urlencode({
        'username': username,
        'to': phone,
        'message': message,
        'from': sender,
    }).encode()
    req = urllib.request.Request(
        'https://api.africastalking.com/version1/messaging',
        data=data,
        headers={
            'ApiKey': api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        print(f'[SMS:africastalking] response: {body[:300]}')
        return body


def _twilio(phone, message, sender, api_key):
    import base64
    import urllib.request
    import urllib.parse

    if ':' not in api_key:
        raise ValueError('Twilio SMS_API_KEY must be ACCOUNT_SID:AUTH_TOKEN')
    sid, token = api_key.split(':', 1)
    from_number = current_app.config.get('SMS_FROM_NUMBER') or sender
    data = urllib.parse.urlencode({
        'To': phone,
        'From': from_number,
        'Body': message,
    }).encode()
    auth = base64.b64encode(f'{sid}:{token}'.encode()).decode()
    req = urllib.request.Request(
        f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',
        data=data,
        headers={
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        print(f'[SMS:twilio] response: {body[:300]}')
        return body


def notify_queue_next(ticket, counter_name=None):
    user = ticket.user
    if not user:
        return
    from utils.notifications import notify
    msg_app = f'You are next! Ticket {ticket.ticket_number}. Please proceed to the counter.'
    if counter_name:
        msg_app = f'You are next! Ticket {ticket.ticket_number} — go to {counter_name}.'
    notify(user.id, 'You are next', msg_app, link=f'/customer/ticket/{ticket.ticket_number}', category='queue')
    if user.phone:
        sms = f'QSMART: Ticket {ticket.ticket_number} — you are NEXT. Please go to the counter now.'
        send_sms(user.phone, sms, message_type='queue_next', related_ref=ticket.ticket_number)


def notify_near_turn(ticket):
    if getattr(ticket, 'near_turn_sms_sent', False) or ticket.status != 'waiting':
        return
    if ticket.position != 3:
        return
    user = ticket.user
    if not user:
        return
    from utils.notifications import notify
    notify(
        user.id,
        'Almost your turn',
        f'Ticket {ticket.ticket_number}: only 2 people ahead. Please head to the premises.',
        category='queue',
    )
    if user.phone:
        send_sms(
            user.phone,
            f'QSMART: Ticket {ticket.ticket_number} — only 2 people ahead. Please arrive on time.',
            message_type='queue_near',
            related_ref=ticket.ticket_number,
        )
    ticket.near_turn_sms_sent = True
    db.session.commit()


def refresh_queue_positions(service_id):
    from models.queue import QueueTicket
    from models.service import Service

    waiting = (
        QueueTicket.query.filter_by(service_id=service_id, status='waiting')
        .order_by(QueueTicket.joined_at.asc())
        .all()
    )
    for i, t in enumerate(waiting, start=1):
        t.position = i
    db.session.commit()
    return waiting
