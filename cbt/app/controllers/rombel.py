from app import db
from app.decorators import role_required
from app.models import RombonganBelajar, Sekolah, User
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_


bp = Blueprint("rombel", __name__)


@bp.route("/json/list", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def json_show():
    rombel_list = []

    sekolah_id = request.args.get("sekolah")
    if sekolah_id != None and sekolah_id != "":
        rombel_list = (
            RombonganBelajar.query.filter(
                RombonganBelajar.sekolah_id == sekolah_id,
                or_(
                    RombonganBelajar.deleted.is_(None), RombonganBelajar.deleted != True
                ),
            )
            .order_by(RombonganBelajar.nama.asc())
            .all()
        )

    ret_arr = []
    for i in rombel_list:
        ret_arr.append({"id": i.id, "nama": i.nama})
    return jsonify(ret_arr)


@bp.route("/", methods=["GET"])
@bp.route("/list", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def show():

    school = request.args.get("school", default="", type=str)

    args = request.args

    rombel_list = []

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    if school != "":
        filter = [
            RombonganBelajar.sekolah_id == school,
            or_(RombonganBelajar.deleted.is_(None), RombonganBelajar.deleted != True),
        ]

        rombel_list: list(User) = (
            RombonganBelajar.query.filter(*filter)
            .order_by(RombonganBelajar.nama.asc())
            .all()
        )

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "rombel/rombel-list.html",
        title="Rombongan Belajar",
        rombel_list=rombel_list,
        school_list=school_list,
        args=args,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
# @role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def add():
    sekolah_id = request.args.get("school")

    form = {"sekolah_id": sekolah_id}
    errors = []

    if request.method == "POST":
        form = request.form

        name = request.form.get("nama")
        sekolah_id = request.form.get("sekolah_id")
        tingkat_pendidikan = request.form.get("tingkat_pendidikan")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if sekolah_id is None or sekolah_id == "":
            errors.append("Sekolah tidak boleh kosong.")

        if tingkat_pendidikan is None or tingkat_pendidikan == "":
            errors.append("Tingkat pendidikan tidak boleh kosong.")

        if len(errors) == 0:
            rombel = RombonganBelajar()
            rombel.nama = name
            rombel.sekolah_id = sekolah_id
            rombel.tingkat_pendidikan = tingkat_pendidikan

            db.session.add(rombel)
            db.session.commit()
            flash("Sukses menyimpan rombongan belajar.", "success")
            return redirect(url_for("rombel.show") + "?school=" + sekolah_id)
        else:
            flash("\\n".join(errors), "error")

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "rombel/rombel-form.html",
        title="Edit Rombongan Belajar",
        form=form,
        id=None,
        errors=errors,
        school_list=school_list,
    )


@bp.route("/edit/<rombel_id>", methods=["GET", "POST"])
@login_required
# @role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def edit(rombel_id):
    rombel: RombonganBelajar = RombonganBelajar.query.filter(
        RombonganBelajar.id == rombel_id,
        or_(RombonganBelajar.deleted.is_(None), RombonganBelajar.deleted != True),
    ).first()
    if rombel is None:
        abort(404)

    form = rombel.__dict__
    errors = []

    if request.method == "POST":
        form = request.form

        name = request.form.get("nama")
        sekolah_id = request.form.get("sekolah_id")
        tingkat_pendidikan = request.form.get("tingkat_pendidikan")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if sekolah_id is None or sekolah_id == "":
            errors.append("Sekolah tidak boleh kosong.")

        if tingkat_pendidikan is None or tingkat_pendidikan == "":
            errors.append("Tingkat pendidikan tidak boleh kosong.")

        if len(errors) == 0:
            rombel.nama = name
            rombel.sekolah_id = sekolah_id
            rombel.tingkat_pendidikan = tingkat_pendidikan

            db.session.commit()
            flash("Sukses menyimpan rombongan belajar.", "success")
            return redirect(url_for("rombel.show") + "?school=" + sekolah_id)
        else:
            flash("\\n".join(errors), "error")

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "rombel/rombel-form.html",
        title="Edit Rombongan Belajar",
        form=form,
        id=rombel.id,
        errors=errors,
        school_list=school_list,
    )


@bp.route("/delete/<rombel_id>", methods=["GET"])
@login_required
# @role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def delete(rombel_id):
    rombel: RombonganBelajar = RombonganBelajar.query.filter(
        RombonganBelajar.id == rombel_id,
        or_(RombonganBelajar.deleted.is_(None), RombonganBelajar.deleted != True),
    ).first()
    if rombel is None:
        abort(404)

    db.session.delete(rombel)
    db.session.commit()

    flash("Sukses menghapus rombongan belajar ({})".format(rombel.nama), "success")

    return redirect(url_for("rombel.show") + "?school=" + rombel.sekolah_id)
