"""Email helper — supports Resend API and SMTP. Logs when neither is configured."""
import json
import urllib.request
import urllib.error
from flask import current_app


def send_email(to_addr, subject, body, html_body=None):
    """
    Send email via Resend (preferred) or SMTP.
    Returns (success: bool, status: str)
    """
    if not to_addr:
        return False, 'no_email'

    provider = (current_app.config.get('EMAIL_PROVIDER') or '').lower()
    resend_key = current_app.config.get('RESEND_API_KEY') or ''
    mail_server = current_app.config.get('MAIL_SERVER') or ''
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@qsmart.zm')

    print(f'[EMAIL] To:{to_addr} Subject:{subject} Body:{(body or "")[:100]}')

    # Prefer Resend when configured
    if provider == 'resend' and resend_key:
        return _send_resend(to_addr, subject, body, html_body, sender, resend_key)

    # Fall back to SMTP
    if mail_server:
        return _send_smtp(to_addr, subject, body, html_body, sender)

    return False, 'log_only'


def send_html_email(to_addr, subject, html_body, text_body=None):
    """Convenience wrapper for HTML emails (e.g. password reset)."""
    return send_email(to_addr, subject, text_body or '', html_body=html_body)


def _send_resend(to_addr, subject, body, html_body, sender, api_key):
    try:
        payload = {
            'from': sender,
            'to': [to_addr],
            'subject': subject,
        }
        if html_body:
            payload['html'] = html_body
            if body:
                payload['text'] = body
        else:
            payload['text'] = body or ''

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            'https://api.resend.com/emails',
            data=data,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = resp.read().decode()
            print(f'[EMAIL:resend] {result[:200]}')
            return True, 'sent'
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        print(f'resend error: {e.code} {err}')
        return False, f'resend_{e.code}'
    except Exception as e:
        print('resend error:', e)
        return False, str(e)


def _send_smtp(to_addr, subject, body, html_body, sender):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        if html_body:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(body or '', 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
        else:
            msg = MIMEText(body or '')

        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to_addr

        server = current_app.config.get('MAIL_SERVER')
        port = current_app.config.get('MAIL_PORT', 587)
        username = current_app.config.get('MAIL_USERNAME') or ''
        password = current_app.config.get('MAIL_PASSWORD') or ''
        use_tls = current_app.config.get('MAIL_USE_TLS', True)

        with smtplib.SMTP(server, port, timeout=20) as s:
            if use_tls:
                s.starttls()
            if username:
                s.login(username, password)
            s.send_message(msg)
        return True, 'sent'
    except Exception as e:
        print('email error:', e)
        return False, str(e)
