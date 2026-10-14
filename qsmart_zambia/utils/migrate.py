from sqlalchemy import text, inspect

def ensure_schema(db):
    engine = db.engine
    insp = inspect(engine)
    def cols(table):
        if table not in insp.get_table_names():
            return set()
        return {c['name'] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        u = cols('users')
        for name, typedef in [
            ('email_verified', 'BOOLEAN DEFAULT 0'),
            ('phone_verified', 'BOOLEAN DEFAULT 0'),
            ('otp_code', 'VARCHAR(10)'),
            ('otp_expires', 'DATETIME'),
            ('otp_channel', 'VARCHAR(10)'),
            ('otp_hash', 'VARCHAR(128)'),
            ('otp_attempts', 'INTEGER DEFAULT 0'),
            ('otp_resend_at', 'DATETIME'),
            ('reset_token', 'VARCHAR(128)'),
            ('reset_token_expires', 'DATETIME'),
            ('preferred_language', "VARCHAR(20) DEFAULT 'en'"),
            ('staff_role', "VARCHAR(30) DEFAULT 'staff'"),
            ('privacy_consent_at', 'DATETIME'),
            ('privacy_consent_version', 'VARCHAR(20)'),
            ('data_purpose', "VARCHAR(80) DEFAULT 'queue_service'"),
        ]:
            if u and name not in u:
                conn.execute(text(f'ALTER TABLE users ADD COLUMN {name} {typedef}'))
        qm = cols('query_messages')
        if qm and 'voice_path' not in qm:
            conn.execute(text('ALTER TABLE query_messages ADD COLUMN voice_path VARCHAR(255)'))
        if qm and 'attachment_path' not in qm:
            conn.execute(text('ALTER TABLE query_messages ADD COLUMN attachment_path VARCHAR(255)'))
        if qm and 'attachment_name' not in qm:
            conn.execute(text('ALTER TABLE query_messages ADD COLUMN attachment_name VARCHAR(200)'))
        if qm and 'attachment_type' not in qm:
            conn.execute(text('ALTER TABLE query_messages ADD COLUMN attachment_type VARCHAR(20)'))
    db.create_all()
