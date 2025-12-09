from functools import wraps
import os

from flask import abort, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from app.models import UjianPeserta

def role_required(roles=[]):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.role in roles:
                return abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in request.headers:
            return abort(403)
        
        if request.headers['token'] != os.environ.get('API_KEY'):
            return abort(403)
        
        return f(*args, **kwargs)

    return decorated_function

def redirect_exam(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # exam_student: list[UjianPeserta] = UjianPeserta.query.filter_by(
        #     user_id=current_user.id, status="BERJALAN"
        # ).first()
        exam_student: list[UjianPeserta] = UjianPeserta.query.filter(UjianPeserta.user_id==current_user.id, UjianPeserta.status=="BERJALAN", or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True)).first()

        if exam_student is not None:
            return redirect(url_for("doing.action", number=1))

        return f(*args, **kwargs)

    return decorated_function
