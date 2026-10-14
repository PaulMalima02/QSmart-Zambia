import re
import secrets
from datetime import datetime

# Username: letters, numbers, underscore only (string), 3–30 chars
USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
# Full name: letters, spaces, hyphens, apostrophes (string), 2–120 chars
FULL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s\-']{1,119}$")
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
# Digits only after stripping + and spaces; Zambian mobile is 9 digits after country code
PHONE_DIGITS_RE = re.compile(r'^\d+$')


def validate_username(username):
    """Username must be a non-empty string of letters, numbers, underscore."""
    if username is None:
        return 'Username is required.'
    if not isinstance(username, str):
        return 'Username must be text (letters, numbers, underscore).'
    username = username.strip()
    if not username:
        return 'Username is required.'
    if username.isdigit():
        return 'Username must include letters, not only numbers.'
    if not USERNAME_RE.match(username):
        return 'Username: 3–30 letters, numbers or underscore only (no spaces or symbols).'
    return None


def validate_full_name(full_name):
    """Full name must be a string of letters (spaces/hyphens allowed)."""
    if full_name is None:
        return 'Full name is required.'
    if not isinstance(full_name, str):
        return 'Full name must be text.'
    full_name = full_name.strip()
    if not full_name:
        return 'Full name is required.'
    if len(full_name) < 2:
        return 'Full name must be at least 2 characters.'
    if full_name.isdigit() or PHONE_DIGITS_RE.match(full_name.replace(' ', '')):
        return 'Full name must be text (letters), not numbers.'
    if not FULL_NAME_RE.match(full_name):
        return 'Full name: use letters only (spaces, hyphens and apostrophes allowed).'
    return None


def validate_phone(phone):
    """
    Phone must be numeric digits (Zambia +260).
    Accepts: 097XXXXXXX, 97XXXXXXX, +26097XXXXXXX, 26097XXXXXXX.
    Returns (error_message or None, normalized_e164 or '').
    """
    if phone is None:
        return 'Mobile number is required.', ''
    raw = str(phone).strip()
    if not raw:
        return 'Mobile number is required.', ''

    # Strip spaces, dashes, parentheses — keep leading + for detection
    cleaned = re.sub(r'[\s\-\(\)]', '', raw)

    # Must be digits only, optional leading +
    if cleaned.startswith('+'):
        digits = cleaned[1:]
    else:
        digits = cleaned

    if not digits.isdigit():
        return 'Phone number must contain digits only (e.g. 097XXXXXXX or +26097XXXXXXX).', ''

    # Normalize to E.164 +260…
    if digits.startswith('0') and len(digits) == 10:
        digits = '260' + digits[1:]
    elif len(digits) == 9:
        digits = '260' + digits
    elif digits.startswith('260') and len(digits) == 12:
        pass
    elif len(digits) == 12 and digits.startswith('260'):
        pass
    else:
        # Allow other lengths if all digits but prefer Zambian format messaging
        if len(digits) < 9 or len(digits) > 15:
            return 'Enter a valid Zambian mobile number (9 digits, e.g. 097XXXXXXX).', ''

    # Zambian mobiles: country 260 + 9-digit subscriber
    if digits.startswith('260') and len(digits) != 12:
        return 'Zambian numbers should be 9 digits after +260 (e.g. +26097XXXXXXX).', ''

    normalized = '+' + digits
    return None, normalized


def normalize_phone(phone):
    """Normalize phone to E.164; returns '' if invalid."""
    err, normalized = validate_phone(phone)
    return normalized if not err else ''


def validate_password(password, min_len=8):
    if not isinstance(password, str):
        return 'Password must be text.'
    if len(password) < min_len:
        return f'Password must be at least {min_len} characters.'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return 'Password must include letters and a number.'
    return None


def make_ticket_number():
    return f'Q-{datetime.utcnow().strftime("%y%m%d")}-{secrets.token_hex(3).upper()}'


def make_query_ref():
    return f'QR-{datetime.utcnow().strftime("%y%m%d")}-{secrets.token_hex(3).upper()}'
