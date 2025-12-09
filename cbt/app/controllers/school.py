from app import db
from app.controllers import question
from app.decorators import role_required
from app.models import Config, Kecamatan, RombonganBelajar, Sekolah, User
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_

bp = Blueprint("school", __name__)
bp.register_blueprint(question.bp, url_prefix="/question")


@bp.route("/", methods=["GET"])
@bp.route("/list", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def show():
    query = []
    if current_user.role == "proktor":
        query.append(Sekolah.id == current_user.sekolah_id)

    school_list = (
        Sekolah.query.filter(
            *query, or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
        )
        .order_by(Sekolah.nama.asc())
        .all()
    )

    res_arr = []
    for i in school_list:
        arr = i.__dict__
        arr["jumlah_siswa"] = User.query.filter(
            User.sekolah_id == arr["id"],
            User.role == "peserta_didik",
            or_(User.deleted.is_(None), User.deleted != True),
        ).count()

        res_arr.append(arr)

    config = Config.query.first()

    return render_template(
        "school/school-list.html",
        title="Daftar Sekolah",
        lesson_list=school_list,
        config=config,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def add():
    form = {}
    errors = []

    if request.method == "POST":
        form = request.form

        nama = request.form.get("nama", default="", type=str)
        npsn = request.form.get("npsn", default="", type=str)
        alamat = request.form.get("alamat", default="", type=str)
        kecamatan = request.form.get("kecamatan_id")
        password = request.form.get("password", default="", type=str)
        email = request.form.get("email", default="", type=str)
        kepala_sekolah = request.form.get("kepala_sekolah", default="", type=str)
        nip_kepala_sekolah = request.form.get("nip_kepala_sekolah", default="", type=str)
        no_hp_kepala_sekolah = request.form.get("no_hp_kepala_sekolah", default="", type=str)

        if nama == "":
            errors.append("Nama tidak boleh kosong")

        if npsn == "":
            errors.append("NPSN tidak boleh kosong")

        if alamat == "":
            errors.append("Alamat tidak boleh kosong")

        if kecamatan == "":
            kecamatan = None
        #     errors.append("Kecamatan tidak boleh kosong")

        if len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        sekolah_exist = Sekolah.query.filter(
            Sekolah.npsn == npsn,
            Sekolah.id != id,
            or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
        ).first()

        if sekolah_exist is not None:
            errors.append("NPSN sudah terpakai.")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            school: Sekolah = Sekolah(
                nama=nama,
                npsn=npsn,
                alamat=alamat,
                kecamatan_id=kecamatan,
                email=email,
                kepala_sekolah=kepala_sekolah,
                nip_kepala_sekolah=nip_kepala_sekolah,
                no_hp_kepala_sekolah=no_hp_kepala_sekolah,
            )

            school.set_password(password)

            db.session.add(school)
            db.session.commit()

            flash("Berhasil menyimpan ({})".format(nama), "success")
            return redirect(url_for("school.show"))

    list_kecamatan = Kecamatan.query.filter(
        or_(Kecamatan.deleted.is_(None), Kecamatan.deleted != True)
    ).all()
    return render_template(
        "school/school-form.html",
        title="Tambah Sekolah",
        id=None,
        form=form,
        list_kecamatan=list_kecamatan,
    )


@bp.route("/edit/<id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "proktor"])
def edit(id):
    school: Sekolah = Sekolah.query.filter(
        Sekolah.id == id, or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
    ).first()
    if school is None:
        abort(404)

    form = school.__dict__
    errors = []

    if request.method == "POST":
        form = request.form

        # nama = request.form.get("nama", default="", type=str)
        # npsn = request.form.get("npsn", default="", type=str)
        alamat = request.form.get("alamat", default="", type=str)
        # kecamatan = request.form.get("kecamatan_id")
        # password = request.form.get("password", default="", type=str)
        # email = request.form.get("email", default="", type=str)
        kepala_sekolah = request.form.get("kepala_sekolah", default="", type=str)
        nip_kepala_sekolah = request.form.get("nip_kepala_sekolah", default="", type=str)
        no_hp_kepala_sekolah = request.form.get("no_hp_kepala_sekolah", default="", type=str)

        # if nama == "":
            # errors.append("Nama tidak boleh kosong")

        # if npsn == "":
            # errors.append("NPSN tidak boleh kosong")

        if alamat == "":
            errors.append("Alamat tidak boleh kosong")

        # if kecamatan == "":
            # kecamatan = None
            # errors.append("Kecamatan tidak boleh kosong")

        # if password != "" and len(password) < 6:
            # errors.append("Password harus lebih dari 6 karakter.")

        # sekolah_exist = Sekolah.query.filter(
        #     Sekolah.npsn == npsn,
        #     Sekolah.id != id,
        #     or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
        # ).first()

        # if sekolah_exist is not None:
            # errors.append("NPSN sudah terpakai.")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            # school.nama = nama
            # school.npsn = npsn
            school.alamat = alamat
            # school.kecamatan_id = kecamatan
            # school.email = email
            school.kepala_sekolah = kepala_sekolah
            school.nip_kepala_sekolah = nip_kepala_sekolah
            school.no_hp_kepala_sekolah = no_hp_kepala_sekolah

            # if password != "":
                # school.set_password(password)

            db.session.commit()

            # flash("Berhasil menyimpan ({})".format(nama), "success")
            flash("Berhasil menyimpan", "success")
            return redirect(url_for("school.show"))

    # list_kecamatan = Kecamatan.query.filter(
    #     or_(Kecamatan.deleted.is_(None), Kecamatan.deleted != True)
    # ).all()

    return render_template(
        "school/school-form.html",
        title="Edit Sekolah",
        form=form,
        id=id,
        # list_kecamatan=list_kecamatan,
    )


@bp.route("/delete/<id>", methods=["GET"])
@login_required
@role_required(roles=["admin"])
def delete(id):
    school: Sekolah = Sekolah.query.filter(
        Sekolah.id == id, or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
    ).first()
    if school is None:
        abort(404)

    school.deleted = True

    user: list[User] = User.query.filter(User.sekolah_id == id).all()
    for i in user:
        i.deleted = True

    rombel: list[RombonganBelajar] = RombonganBelajar.query.filter(
        RombonganBelajar.sekolah_id == id
    ).all()
    for i in rombel:
        i.deleted = True

    db.session.commit()

    flash("Berhasil menghapus pelajaran ({})".format(school.nama), "success")

    return redirect(url_for("school.show"))
