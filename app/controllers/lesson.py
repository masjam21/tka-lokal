from app import db
from app.controllers import question
from app.decorators import role_required
from app.models import Pelajaran, Pertanyaan
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

bp = Blueprint("lesson", __name__)
bp.register_blueprint(question.bp, url_prefix="/question")


@bp.route("/", methods=["GET"])
@bp.route("/list", methods=["GET"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def show():
    lesson_list = []
    for i in (
        Pelajaran.query.filter(
            or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True)
        )
        .order_by(Pelajaran.kode.asc())
        .all()
    ):
        l = i.__dict__
        l["jumlah_soal"] = Pertanyaan.query.filter(
            Pertanyaan.pelajaran_id == i.id,
            or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
        ).count()

        lesson_list.append(l)

    return render_template(
        "lesson/lesson-list.html",
        title="Daftar Pelajaran",
        lesson_list=lesson_list,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def add():
    form = {}
    errors = []

    if request.method == "POST":
        form = request.form
        code = request.form.get("kode", default="", type=str)
        name = request.form.get("nama", default="", type=str)

        if code == "":
            errors.append("Kode pelajaran tidak boleh kosong")
        if name == "":
            errors.append("Nama pelajaran tidak boleh kosong")

        lesson = Pelajaran.query.filter(
            Pelajaran.kode == code,
            or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
        ).first()
        if lesson is not None:
            errors.append("Kode pelajaran sudah terpakai.")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            lesson = Pelajaran(kode=code, nama=name)
            db.session.add(lesson)
            db.session.commit()

            flash("Berhasil menambahkan ({})".format(name), "success")
            return redirect(url_for("lesson.show"))

    return render_template(
        "lesson/lesson-form.html",
        title="Tambah Pelajaran",
        id=None,
        form=form,
    )


@bp.route("/edit/<id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def edit(id):
    lesson: Pelajaran = Pelajaran.query.filter(
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True), Pelajaran.id == id
    ).first()
    if lesson is None:
        abort(404)

    form = lesson.__dict__
    errors = []

    if request.method == "POST":
        form = request.form
        code = request.form.get("kode", default="", type=str)
        name = request.form.get("nama", default="", type=str)

        if code == "":
            errors.append("Kode pelajaran tidak boleh kosong")
        if name == "":
            errors.append("Nama pelajaran tidak boleh kosong")

        lesson_exist = Pelajaran.query.filter(
            Pelajaran.kode == code,
            Pelajaran.id != lesson.id,
            or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
        ).first()
        if lesson_exist is not None:
            errors.append("Kode pelajaran sudah terpakai.")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            lesson.kode = code
            lesson.nama = name
            db.session.commit()

            flash("Berhasil menyimpan ({})".format(name), "success")
            return redirect(url_for("lesson.show"))

    return render_template(
        "lesson/lesson-form.html",
        title="Edit Pelajaran",
        form=form,
        id=id,
    )


@bp.route("/delete/<id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def delete(id):
    lesson: Pelajaran = Pelajaran.query.filter(
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True), Pelajaran.id == id
    ).first()
    if lesson is None:
        abort(404)

    lesson.deleted = True

    question: list[Pertanyaan] = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == lesson.id
    ).all()
    for i in question:
        i.deleted = True

    db.session.commit()

    flash("Berhasil menghapus pelajaran ({})".format(lesson.nama), "success")

    return redirect(url_for("lesson.show"))
