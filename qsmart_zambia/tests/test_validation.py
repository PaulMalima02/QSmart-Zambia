"""Field validation: full name string, username string, phone digits."""
from utils.helpers import validate_username, validate_full_name, validate_phone


def test_username_must_be_string_not_digits_only():
    assert validate_username('12345') is not None
    assert validate_username('ab') is not None  # too short
    assert validate_username('john_doe') is None
    assert validate_username('Alice01') is None


def test_full_name_must_be_letters():
    assert validate_full_name('12345') is not None
    assert validate_full_name('') is not None
    assert validate_full_name('Jane Banda') is None
    assert validate_full_name("O'Brien") is None


def test_phone_must_be_digits_zambia():
    err, n = validate_phone('0971234567')
    assert err is None
    assert n == '+260971234567'
    err, n = validate_phone('+260971234567')
    assert err is None
    err, n = validate_phone('not-a-phone')
    assert err is not None
    err, n = validate_phone('')
    assert err is not None
