import csv
import datetime
import logging
import traceback

from app import db
from app.decorators import role_required
from app.models import RombonganBelajar, Sekolah, User
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

bp = Blueprint("student", __name__)


@bp.route("/", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def show():

    school = request.args.get("school", default="", type=str)

    args = request.args

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    student_list = []

    if school != "":
        filter = [
            User.role == "peserta_didik",
            User.sekolah_id == school,
            or_(
                User.deleted.is_(None),
                or_(User.deleted.is_(None), User.deleted != True),
            ),
        ]

        student_list: list(User) = (
            User.query.filter(*filter).order_by(User.nama.asc()).all()
        )

    school_list = (
        Sekolah.query.filter(
            or_(
                Sekolah.deleted.is_(None),
                or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
            )
        )
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "student/student-list.html",
        title="Peserta",
        student_list=student_list,
        school_list=school_list,
        args=args,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
#@role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def add():
    school = request.args.get("school", default="", type=str)

    form = {"sekolah_id": school}
    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        name = request.form.get("nama")
        password = request.form.get("password")
        sekolah_id = request.form.get("sekolah_id")
        nik = request.form.get("nik")
        ibu = request.form.get("ibu")
        ayah = request.form.get("ayah")
        alamat = request.form.get("alamat")
        jenis_kelamin = request.form.get("jenis_kelamin")
        rombongan_belajar_id = request.form.get("rombongan_belajar_id")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir_str = request.form.get("tanggal_lahir_str")

        if username is None or username == "":
            errors.append("Username tidak boleh kosong")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if password is None or len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        if sekolah_id is None or sekolah_id == "":
            errors.append("Sekolah tidak boleh kosong.")

        if rombongan_belajar_id is None or rombongan_belajar_id == "":
            errors.append("Rombongan Belajar tidak boleh kosong.")

        if jenis_kelamin not in ["L", "P"]:
            errors.append("Jenis kelamin tidak boleh kosong.")

        tanggal_lahir = None
        if tanggal_lahir_str != None and tanggal_lahir_str != "":
            try:
                tanggal_lahir = datetime.datetime.strptime(
                    tanggal_lahir_str, "%m/%d/%Y"
                )
            except Exception:
                errors.append("Format tanggal tidak sesuai.")

        user_exist = User.query.filter(
            User.username == username,
            or_(User.deleted.is_(None), User.deleted != True),
        ).first()

        if user_exist is not None:
            errors.append("Username telah terpakai.")

        if len(errors) == 0:
            user = User()
            user.username = username
            user.nama = name
            user.role = "peserta_didik"
            user.sekolah_id = sekolah_id
            user.rombongan_belajar_id = rombongan_belajar_id
            user.jenis_kelamin = jenis_kelamin

            user.nik = nik
            user.ibu = ibu
            user.ayah = ayah
            user.alamat = alamat
            user.tempat_lahir = tempat_lahir
            user.tanggal_lahir = tanggal_lahir

            user.set_password(password)

            db.session.add(user)
            db.session.commit()
            flash("Sukses menyimpan peserta.", "success")
            return redirect(url_for("student.show") + "?school=" + sekolah_id)
        else:
            flash("\\n".join(errors), "error")

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "student/student-form.html",
        title="Tambah Peserta",
        form=form,
        id=None,
        school_list=school_list,
    )


@bp.route("/edit/<student_id>", methods=["GET", "POST"])
@login_required
#@role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def edit(student_id):
    user: User = User.query.filter(
        User.id == student_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()
    if user is None:
        abort(404)

    form = user.__dict__
    form["tanggal_lahir_str"] = (
        datetime.datetime.strftime(form["tanggal_lahir"], "%m/%d/%Y")
        if form["tanggal_lahir"] is not None
        else ""
    )

    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        name = request.form.get("nama")
        password = request.form.get("password")
        sekolah_id = request.form.get("sekolah_id")
        nik = request.form.get("nik")
        ibu = request.form.get("ibu")
        ayah = request.form.get("ayah")
        alamat = request.form.get("alamat")
        jenis_kelamin = request.form.get("jenis_kelamin")
        rombongan_belajar_id = request.form.get("rombongan_belajar_id")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir_str = request.form.get("tanggal_lahir_str")

        if username is None or username == "":
            errors.append("Username tidak boleh kosong")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if password is not None and password != "" and len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        if sekolah_id is None or sekolah_id == "":
            errors.append("Sekolah tidak boleh kosong.")

        if sekolah_id == current_user.sekolah_id:
            errors.append("Sekolah tidak sesuai dengan identitas proktor.")

        if rombongan_belajar_id is None or rombongan_belajar_id == "":
            errors.append("Rombongan Belajar tidak boleh kosong.")

        if jenis_kelamin not in ["L", "P"]:
            errors.append("Jenis kelamin tidak boleh kosong.")

        tanggal_lahir = None
        if tanggal_lahir_str != None and tanggal_lahir_str != "":
            try:
                tanggal_lahir = datetime.datetime.strptime(
                    tanggal_lahir_str, "%m/%d/%Y"
                )
            except Exception:
                errors.append("Format tanggal tidak sesuai.")

        user_exist = User.query.filter(
            User.id != student_id,
            User.username == username,
            or_(User.deleted.is_(None), User.deleted != True),
        ).first()

        if user_exist is not None:
            errors.append("Username telah terpakai.")

        if len(errors) == 0:
            user.username = username
            user.nama = name
            user.sekolah_id = sekolah_id
            user.rombongan_belajar_id = rombongan_belajar_id
            user.jenis_kelamin = jenis_kelamin

            user.nik = nik
            user.ibu = ibu
            user.ayah = ayah
            user.alamat = alamat
            user.tempat_lahir = tempat_lahir
            user.tanggal_lahir = tanggal_lahir

            if password is not None and password != "":
                user.set_password(password)

            db.session.commit()
            flash("Sukses menyimpan peserta.", "success")
            return redirect(url_for("student.show") + "?school=" + sekolah_id)
        else:
            flash("\\n".join(errors), "error")

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "student/student-form.html",
        title="Edit Peserta",
        form=form,
        id=user.id,
        errors=errors,
        school_list=school_list,
    )


@bp.route("/delete/<student_id>", methods=["GET"])
@login_required
#@role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def delete(student_id):
    student: User = User.query.filter(
        User.id == student_id,
        User.role == "peserta_didik",
        or_(User.deleted.is_(None), User.deleted != True),
    ).first()
    if student is None:
        abort(404)

    db.session.delete(student)
    db.session.commit()

    flash("Sukses menghapus peserta ({})".format(student.nama), "success")

    return redirect(url_for("student.show") + "?school=" + student.sekolah_id)


@bp.route("/import", methods=["GET", "POST"])
@login_required
#@role_required(roles=["admin", "proktor"])
@role_required(roles=["admin"])
def import_():
    form = {}
    errors = []

    if request.method == "POST":
        pemisah = request.form.get("pemisah", ";", type=str)
        f = None
        if "file" not in request.files:
            errors.append("File tidak boleh kosong.")
        else:
            f = request.files["file"]

            if f.filename == "":
                errors.append("File tidak boleh kosong.")
            elif not (
                "." in f.filename and f.filename.rsplit(".", 1)[1].lower() in ["csv"]
            ):
                errors.append("Format file yang diperbolehkan '.csv'")

        if len(errors) == 0:
            fstring = f.read().decode("utf-8")
            for row in csv.DictReader(
                fstring.splitlines(), skipinitialspace=True, delimiter=pemisah
            ):
                if (
                    "id" in row
                    and "nama" in row
                    and "password" in row
                    and "npsn" in row
                    and "rombel" in row
                ):
                    user: User = User.query.filter(
                        User.username == row["id"],
                        or_(User.deleted.is_(None), User.deleted != True),
                    ).first()
                    if user is not None:
                        user.username = row["id"]
                        user.nama = row["nama"]
                        user.nis = row["nis"]
                        user.nik = row["nik"]
                        user.ibu = row["ibu"]
                        user.ayah = row["ayah"]
                        user.alamat = row["alamat"]
                        user.jenis_kelamin = (
                            row["jenis_kelamin"]
                            if row["jenis_kelamin"] in ["L", "P"]
                            else None
                        )
                        user.role = "peserta_didik"
                        user.tempat_lahir = row["tempat_lahir"]
                        try:
                            tanggal_lahir = datetime.datetime.strptime(
                                row["tanggal_lahir"], "%d/%m/%Y"
                            )
                            user.tanggal_lahir = tanggal_lahir
                        except Exception as e:
                            logging.error(traceback.format_exc())

                        sekolah = Sekolah.query.filter(
                            Sekolah.npsn == row["npsn"],
                            or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
                        ).first()
                        if sekolah is not None:
                            user.sekolah_id = sekolah.id

                            rombel = RombonganBelajar.query.filter(
                                RombonganBelajar.sekolah_id == sekolah.id,
                                RombonganBelajar.nama == row["rombel"],
                                or_(
                                    RombonganBelajar.deleted.is_(None),
                                    RombonganBelajar.deleted != True,
                                ),
                            ).first()
                            if rombel is not None:
                                user.rombongan_belajar_id = rombel.id

                        user.set_password(row["password"])
                        db.session.commit()
                    else:
                        sekolah = Sekolah.query.filter(
                            Sekolah.npsn == row["npsn"],
                            or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
                        ).first()
                        if sekolah is not None:

                            user: User = User()
                            user.role = "peserta_didik"
                            user.username = row["id"]
                            user.sekolah_id = sekolah.id

                            rombel = RombonganBelajar.query.filter(
                                RombonganBelajar.sekolah_id == sekolah.id,
                                RombonganBelajar.nama == row["rombel"],
                                or_(
                                    RombonganBelajar.deleted.is_(None),
                                    RombonganBelajar.deleted != True,
                                ),
                            ).first()

                            if rombel is not None:
                                user.rombongan_belajar_id = rombel.id

                            user.nama = row["nama"]
                            user.nik = row["nik"]
                            user.nis = row["nis"]
                            user.ibu = row["ibu"]
                            user.ayah = row["ayah"]
                            user.alamat = row["alamat"]
                            user.jenis_kelamin = (
                                row["jenis_kelamin"]
                                if row["jenis_kelamin"] in ["L", "P"]
                                else None
                            )
                            user.tempat_lahir = row["tempat_lahir"]
                            try:
                                tanggal_lahir = datetime.datetime.strptime(
                                    row["tanggal_lahir"], "%d/%m/%Y"
                                )
                                user.tanggal_lahir = tanggal_lahir
                            except Exception as e:
                                logging.error(traceback.format_exc())

                            user.set_password(row["password"])

                            db.session.add(user)
                            db.session.commit()

            flash("Berhasil import peserta", "success")

            return redirect(url_for("student.show"))
        else:
            flash("\\n".join(errors), "error")

    return render_template(
        "student/student-import.html", title="Import Peserta", form=form
    )

@bp.route("/detail/<student_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "proktor"])
def detail(student_id):
    user: User = User.query.filter(
        User.id == student_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()
    if user is None:
        abort(404)

    form = user.__dict__
    form["tanggal_lahir_str"] = (
        datetime.datetime.strftime(form["tanggal_lahir"], "%d/%m/%Y")
        if form["tanggal_lahir"] is not None
        else ""
    )

    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("nama")
        sekolah_id = request.form.get("sekolah_id")
        rombongan_belajar_id = request.form.get("rombongan_belajar_id")
        nis = request.form.get("nis")
        nik = request.form.get("nik")
        ibu = request.form.get("ibu")
        ayah = request.form.get("ayah")
        alamat = request.form.get("alamat")
        jenis_kelamin = request.form.get("jenis_kelamin")
        tempat_lahir = request.form.get("tempat_lahir")
        tanggal_lahir_str = request.form.get("tanggal_lahir_str")

        if username is None or username == "":
            errors.append("Username tidak boleh kosong")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if password is not None and password != "" and len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        if sekolah_id is None or sekolah_id == "":
            errors.append("Sekolah tidak boleh kosong.")

        if rombongan_belajar_id is None or rombongan_belajar_id == "":
            errors.append("Rombongan Belajar tidak boleh kosong.")

        if jenis_kelamin not in ["L", "P"]:
            errors.append("Jenis kelamin tidak boleh kosong.")

        tanggal_lahir = None
        if tanggal_lahir_str != None and tanggal_lahir_str != "":
            try:
                tanggal_lahir = datetime.datetime.strptime(
                    tanggal_lahir_str, "%d/%m/%Y"
                )
            except Exception:
                errors.append("Format tanggal tidak sesuai.")

        user_exist = User.query.filter(
            User.id != student_id,
            User.username == username,
            or_(User.deleted.is_(None), User.deleted != True),
        ).first()

        if user_exist is not None:
            errors.append("Username telah terpakai.")

        if len(errors) == 0:
            if password is not None and password != "":
                user.set_password(password)

            db.session.commit()
            flash("Sukses menyimpan peserta.", "success")
            return redirect(url_for("student.show") + "?school=" + sekolah_id)
        else:
            flash("\\n".join(errors), "error")

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    return render_template(
        "student/student-detail.html",
        title="Detail Peserta Didik",
        form=form,
        errors=errors,
        school_list=school_list,
    )