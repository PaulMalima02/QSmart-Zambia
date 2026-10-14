"""PII masking for logs and UI — show minimal identifiable data."""


def mask_phone(phone):
    if not phone:
        return '—'
    p = str(phone).strip()
    if len(p) < 6:
        return '***'
    return p[:4] + '****' + p[-3:]


def mask_email(email):
    if not email or '@' not in email:
        return '—'
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked = local[0] + '***'
    else:
        masked = local[0] + '***' + local[-1]
    return f'{masked}@{domain}'


def mask_name(name):
    if not name:
        return '—'
    parts = str(name).strip().split()
    if not parts:
        return '—'
    return parts[0][0] + '***'


def public_ticket_label(ticket):
    """Public screens: ticket number only, never personal names."""
    return getattr(ticket, 'ticket_number', '—')
