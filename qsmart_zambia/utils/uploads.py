import os
from werkzeug.utils import secure_filename
from flask import current_app


def _ext(filename):
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()


def save_query_attachment(file_storage, user_id, ref_prefix='q'):
    """
    Save voice, image or document. Returns dict:
    {path, name, type} or None.
    """
    if not file_storage or not file_storage.filename:
        return None
    ext = _ext(file_storage.filename)
    voice = current_app.config.get('ALLOWED_VOICE', set())
    images = current_app.config.get('ALLOWED_IMAGES', set())
    docs = current_app.config.get('ALLOWED_DOCS', set())

    if ext in voice:
        kind, sub = 'voice', 'voice'
    elif ext in images:
        kind, sub = 'image', 'images'
    elif ext in docs:
        kind, sub = 'document', 'docs'
    else:
        return {'error': f'File type .{ext} is not allowed.'}

    base = current_app.config.get('UPLOAD_FOLDER') or str(
        current_app.root_path + '/static/uploads'
    )
    folder = os.path.join(base, sub)
    os.makedirs(folder, exist_ok=True)
    original = secure_filename(file_storage.filename) or f'file.{ext}'
    fname = secure_filename(f'{user_id}_{ref_prefix}_{original}')
    if not fname.endswith(f'.{ext}'):
        fname = f'{fname}.{ext}'
    file_storage.save(os.path.join(folder, fname))
    return {
        'path': f'uploads/{sub}/{fname}',
        'name': original,
        'type': kind,
        'voice_path': f'uploads/{sub}/{fname}' if kind == 'voice' else None,
    }
