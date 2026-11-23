from utils.database import db


def notify(user_id, title, body='', link=None, category='general'):
    try:
        from models.notification import Notification
        n = Notification(user_id=user_id, title=title, body=body, link=link, category=category)
        db.session.add(n)
        db.session.commit()
        return n
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        print('notify error:', e)
        return None
