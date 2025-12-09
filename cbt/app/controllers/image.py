import base64
from io import BytesIO
from os import abort

from app import csrf, db
from app.models import Gambar
from flask import Blueprint, request, send_file
from flask_login import login_required
from sqlalchemy import or_

bp = Blueprint("image", __name__)


@bp.route("/upload/<pelajaran_id>", methods=["POST"])
@login_required
@csrf.exempt
def upload(pelajaran_id):
    if request.method == "POST":
        file = request.files["image"]
        if file.filename == "":
            return "error.png"
        if file and file.filename.rsplit(".", 1)[1].lower() in [
            "png",
            "jpg",
            "jpeg",
            "gif",
        ]:
            data_gambar = base64.b64encode(file.read()).decode("ascii")

            im = Gambar(
                nama=file.filename,
                data_gambar=data_gambar,
                pelajaran_id=pelajaran_id,
            )
            db.session.add(im)
            db.session.commit()
            return im.id

    return "", 400


@bp.route("/get/<gambar_id>", methods=["GET"])
@login_required
@csrf.exempt
def get(gambar_id):
    gambar: Gambar = Gambar.query.filter(
        Gambar.id == gambar_id, or_(Gambar.deleted.is_(None), Gambar.deleted != True)
    ).first()
    if gambar is None:
        abort(404)

    return send_file(
        BytesIO(base64.b64decode(gambar.data_gambar)),
        attachment_filename=gambar.nama,
        as_attachment=True,
    )
