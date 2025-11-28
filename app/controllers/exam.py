import uuid
from datetime import datetime, date
from os import environ
import io
from io import BytesIO
import os

import requests
from app import db
from app.controllers import schedule
from app.decorators import role_required
from app.models import (
    JadwalUjian,
    Jawaban,
    Pelajaran,
    PelajaranUjian,
    Sekolah,
    Ujian,
    UjianPeserta,
    UjianSekolah,
    User,
    Pertanyaan,
)
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    Response,
    send_file,
)
from flask_login import current_user, login_required
from sqlalchemy import or_, create_engine, text
from sqlalchemy.orm import sessionmaker
import sqlalchemy
import xlwt
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from terbilang import Terbilang
from decimal import Decimal, ROUND_HALF_UP

bp = Blueprint("exam", __name__)
bp.register_blueprint(schedule.bp, url_prefix="/schedule")

@bp.route("/", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def show():
    exam_list: list(Ujian) = (
        Ujian.query.filter(or_(Ujian.deleted.is_(None), Ujian.deleted != True))
        .order_by(Ujian.nama.asc())
        .all()
    )
    return render_template("exam/exam-list.html", title="Ujian", exam_list=exam_list)


@bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def add():
    form = {}
    errors = []

    if request.method == "POST":
        form = {}
        nama = request.form.get("nama", default="", type=str)
        pelajaran = request.form.getlist("pelajaran")

        form["nama"] = nama
        form["pelajaran"] = pelajaran

        if nama == "":
            errors.append("Nama tidak boleh kosong.")
        if len(pelajaran) == 0:
            errors.append("Pelajaran tidak boleh kosong.")

        if len(errors) == 0:
            ujian = Ujian()
            ujian.nama = nama
            db.session.add(ujian)
            db.session.flush()

            for i in pelajaran:
                pelajaran_ujian = PelajaranUjian()
                pelajaran_ujian.pelajaran_id = i
                pelajaran_ujian.ujian_id = ujian.id
                db.session.add(pelajaran_ujian)

            db.session.commit()
            flash("Berhasil menyimpan ujian.", "success")
            return redirect(url_for("exam.show"))
        else:
            flash("\\n".join(errors), "error")

    lesson_list = (
        Pelajaran.query.filter(
            or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True)
        )
        .order_by(Pelajaran.kode.asc())
        .all()
    )

    return render_template(
        "exam/exam-form.html",
        title="Tambah Ujian",
        form=form,
        id=None,
        lesson_list=lesson_list,
    )


@bp.route("/edit/<exam_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def edit(exam_id):
    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    pelajaran = PelajaranUjian.query.filter(
        PelajaranUjian.ujian_id == exam_id,
        or_(PelajaranUjian.deleted.is_(None), PelajaranUjian.deleted != True),
    ).all()

    form = exam.__dict__
    pelajaran_arr = []
    for i in pelajaran:
        pelajaran_arr.append(str(i))
    form["pelajaran"] = pelajaran_arr

    errors = []

    if request.method == "POST":
        form = {}
        nama = request.form.get("nama", default="", type=str)
        pelajaran = request.form.getlist("pelajaran")

        form["nama"] = nama
        form["pelajaran"] = pelajaran

        if nama == "":
            errors.append("Nama tidak boleh kosong.")
        if len(pelajaran) == 0:
            errors.append("Pelajaran tidak boleh kosong.")

        if len(errors) == 0:
            exam.nama = nama

            for i in pelajaran:
                if i in pelajaran_arr:
                    pelajaran_arr.remove(i)

                else:
                    pelajaran_ujian: PelajaranUjian = PelajaranUjian.query.filter(
                        PelajaranUjian.pelajaran_id == i,
                        PelajaranUjian.ujian_id == exam.id,
                        PelajaranUjian.deleted == True,
                    ).first()
                    if pelajaran_ujian is not None:
                        pelajaran_ujian.deleted = False
                    else:
                        pelajaran_ujian = PelajaranUjian()
                        pelajaran_ujian.pelajaran_id = i
                        pelajaran_ujian.ujian_id = exam.id

                        db.session.add(pelajaran_ujian)

            for i in pelajaran_arr:
                pelajaran_ujian: PelajaranUjian = PelajaranUjian.query.filter(
                    PelajaranUjian.pelajaran_id == i,
                    PelajaranUjian.ujian_id == exam.id,
                    or_(
                        PelajaranUjian.deleted.is_(None), PelajaranUjian.deleted != True
                    ),
                ).first()
                if pelajaran_ujian is not None:
                    jadwal_ujian_count = JadwalUjian.query.filter(
                        JadwalUjian.pelajaran_id == pelajaran_ujian.pelajaran_id,
                        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
                    ).count()

                    if jadwal_ujian_count > 0:
                        errors.append("Pelajaran terpakai.")
                    else:
                        pelajaran_ujian.deleted = True

            if len(errors) == 0:
                db.session.commit()
                flash("Berhasil menyimpan ujian.", "success")
                return redirect(url_for("exam.show"))
            else:
                flash("\\n".join(errors), "error")

        else:
            flash("\\n".join(errors), "error")

    lesson_list = (
        Pelajaran.query.filter(
            or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True)
        )
        .order_by(Pelajaran.kode.asc())
        .all()
    )

    return render_template(
        "exam/exam-form.html",
        title="Edit Ujian",
        form=form,
        id=id,
        lesson_list=lesson_list,
    )


@bp.route("/delete/<exam_id>", methods=["GET"])
@login_required
@role_required(roles=["admin"])
def delete(exam_id):
    ujian: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if ujian is None:
        abort(404)

    # db.session.delete(ujian)
    pelajaran_ujian: list[PelajaranUjian] = PelajaranUjian.query.filter(
        PelajaranUjian.ujian_id == exam_id
    ).all()
    for i in pelajaran_ujian:
        i.deleted = True

    jadwal_ujian: list[JadwalUjian] = JadwalUjian.query.filter(
        JadwalUjian.ujian_id == exam_id
    ).all()
    for i in jadwal_ujian:
        i.deleted = True

    ujian.deleted = True
    db.session.commit()

    flash("Sukses menghapus peserta ({})".format(ujian.nama), "success")

    return redirect(url_for("exam.show"))


@bp.route("/result/<exam_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def student_list(exam_id):

    school = request.args.get("school", default="", type=str)

    args = request.args

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    exam = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()

    student_list = {}

    title = "Hasil Ujian"
    if school != "":
        sekolah = Sekolah.query.filter(
            Sekolah.id == school,
            or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
        ).first()

        filter = [
            User.role == "peserta_didik",
            User.sekolah_id == school,
            or_(User.deleted.is_(None), User.deleted != True),
        ]

        student: list[User] = User.query.filter(*filter).order_by(User.nama.asc()).all()
        student_lst = {}

        for i in student:
            student_lst[i.id] = {**i.__dict__}
            student_lst[i.id]["hasil"] = {}
            rombongan_belajar = i.rombongan_belajar
            student_lst[i.id]["rombongan_belajar"] = ""
            if rombongan_belajar is not None:
                student_lst[i.id]["rombongan_belajar"] = rombongan_belajar.nama

        ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
            UjianPeserta.ujian_id == exam_id,
            UjianPeserta.sekolah_id == school,
            or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
            UjianPeserta.status == "SELESAI",
        ).all()

        # mod by grey
        # jawaban: list[Jawaban] = Jawaban.query.filter(
        #    Jawaban.ujian_peserta_id.in_(ujian_peserta.id),
        #    or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
        #).all()
        # end mod

        for i in ujian_peserta:
            student_list[i.user_id] = student_lst[i.user_id]

        for i in ujian_peserta:
            student_list[i.user_id]["hasil"][i.pelajaran_id] = i.hasil

        for i in ujian_peserta:
            student_list[i.user_id]["ujian_peserta_id"] = i.id

        # for i in jawaban:
            # student_list[i.user_id]["uraian"] = 

        title = "Hasil Ujian {} {}".format(exam.nama, sekolah.nama)

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )
    ujian_list = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()

    return render_template(
        "exam/exam-result-list.html",
        title=title,
        student_list=student_list,
        school_list=school_list,
        args=args,
        ujian_list=ujian_list,
        exam_id=exam_id,
    )


# @bp.route("/print/<exam_id>", methods=["GET"])
# @login_required
# @role_required(roles=["admin", "proktor"])
# def print_all(exam_id):

#     school = request.args.get("school", default="", type=str)

#     args = request.args

#     if current_user.role == "proktor":
#         school = current_user.sekolah_id
#         args = {"school": school}

#     student_list = {}

#     if school != "":
#         filter = [
#             User.role == "peserta_didik",
#             User.sekolah_id == school,
#             or_(User.deleted.is_(None), User.deleted != True),
#         ]

#         student: list[User] = User.query.filter(*filter).order_by(User.nama.asc()).all()

#         student_lst = {}
#         for i in student:
#             student_lst[i.id] = {**i.__dict__}
#             student_lst[i.id]["hasil"] = {}
#             student_lst[i.id]["rombongan_belajar"] = (
#                 i.rombongan_belajar.nama if i.rombongan_belajar is not None else ""
#             )
#             student_lst[i.id]["sekolah"] = i.sekolah.__dict__
#             student_lst[i.id]["tanggal_lahir"] = (
#                 datetime.strftime(i.tanggal_lahir, "%d-%m-%Y")
#                 if i.tanggal_lahir is not None
#                 else ""
#             )
#             student_lst[i.id]["total"] = 0

#         school_list = (
#             Sekolah.query.filter(
#                 or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
#             )
#             .order_by(Sekolah.nama.asc())
#             .all()
#         )
#         ujian_list = Ujian.query.filter(
#             Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
#         ).first()

#         print(ujian_list)

#         ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
#             UjianPeserta.ujian_id == exam_id,
#             UjianPeserta.sekolah_id == school,
#             or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#             UjianPeserta.status == "SELESAI",
#         ).all()

#         for i in ujian_peserta:
#             student_list[i.user_id] = student_lst[i.user_id]

#         for i in ujian_peserta:
#             student_list[i.user_id]["hasil"][i.pelajaran_id] = i.hasil
#             student_list[i.user_id]["total"] += i.hasil if i.hasil is not None else 0

#     now_string = datetime.strftime(datetime.now(), "%d-%m-%Y")

#     return render_template(
#         "exam/exam-result-print.html",
#         title="Hasil Ujian",
#         student_list=student_list,
#         school_list=school_list,
#         args=args,
#         ujian_list=ujian_list,
#         exam_id=exam_id,
#         now_string=now_string,
#     )
@bp.route("/print/<exam_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def print_all(exam_id):

    school = request.args.get("school", default="", type=str)

    args = request.args

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    student_list = {}

    if school != "":
        filter = [
            User.role == "peserta_didik",
            User.sekolah_id == school,
            or_(User.deleted.is_(None), User.deleted != True),
        ]

        student: list[User] = User.query.filter(*filter).order_by(User.nama.asc()).all()

        student_lst = {}
        for i in student:
            student_lst[i.id] = {**i.__dict__}
            student_lst[i.id]["hasil"] = {}
            student_lst[i.id]["rombongan_belajar"] = (
                i.rombongan_belajar.nama if i.rombongan_belajar is not None else ""
            )
            student_lst[i.id]["sekolah"] = i.sekolah.__dict__
            student_lst[i.id]["tanggal_lahir"] = (
                datetime.strftime(i.tanggal_lahir, "%d-%m-%Y")
                if i.tanggal_lahir is not None
                else ""
            )
            student_lst[i.id]["total"] = 0

        school_list = (
            Sekolah.query.filter(
                or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
            )
            .order_by(Sekolah.nama.asc())
            .all()
        )
        ujian_list = Ujian.query.filter(
            Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
        ).first()

        print(ujian_list)

        ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
            UjianPeserta.ujian_id == exam_id,
            UjianPeserta.sekolah_id == school,
            or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
            UjianPeserta.status == "SELESAI",
        ).all()

        for i in ujian_peserta:
            student_list[i.user_id] = student_lst[i.user_id]

        for i in ujian_peserta:
            student_list[i.user_id]["hasil"][i.pelajaran_id] = i.hasil
            student_list[i.user_id]["total"] += i.hasil if i.hasil is not None else 0

    now_string = datetime.strftime(datetime.now(), "%d-%m-%Y")
    # now_string = datetime.strftime(date(2024, 6, 10), "%d-%m-%Y")

    # modified by grey
    sql_identitas = text(
        """select up.user_id, s.nama, s.alamat, s.kepala_sekolah, s.nip_kepala_sekolah, u.nama, u.username, u.nis, u.ayah, u.tempat_lahir, u.tanggal_lahir, truncate(sum(up.hasil), 2)
        from ujian_peserta up
        left join sekolah s on up.sekolah_id = s.id
        left join user u on up.user_id = u.id
        left join ujian uj on up.ujian_id = uj.id
        where up.deleted = 0
        group by up.user_id, s.nama, s.alamat, s.kepala_sekolah, s.nip_kepala_sekolah, u.nama, u.username, u.nis, u.ayah, u.tempat_lahir, u.tanggal_lahir
        order by u.nama asc"""
    )
    identitas = db.engine.execute(sql_identitas)

    sql_hasil = text(
        """select up.user_id, substring_index(trim(uj.nama), ' ', -2), truncate(up.hasil, 2)
        from ujian_peserta up
        left join ujian uj on up.ujian_id = uj.id
        where up.deleted = 0 order by uj.nama asc
        """
    )
    hasil = db.engine.execute(sql_hasil)
    t = Terbilang(sep='.')
    k = 2
    # hasil_list = [
    #     {
    #         "id": row[0],
    #         "ujian": row[1],
    #         "hasil": row[2],
    #         "terbilang": t.parse(row[2]).getresult()
    #     }
    #     for row in hasil
    # ]
    # hasil_list = [
    #     {
    #         "id": row[0],
    #         "ujian": row[1],
    #         "hasil": "{{:.{}f}}".format(k).format(row[2]) if row[2] is not None else 0,   
    #         "terbilang": t.parse("{{:.{}f}}".format(k).format(row[2])).getresult() if row[2] is not None else 0
    #     }
    #     for row in hasil
    # ]
    hasil_list = [
        {
            "id": row[0],
            "ujian": row[1],
            "hasil": "{{:.{}f}}".format(k).format(row[2] if row[2] is not None else 0.0),
            "terbilang": t.parse("{{:.{}f}}".format(k).format(row[2] if row[2] is not None else 0.0)).getresult()
        }
        for row in hasil
    ]

    # identitas_list = [
    #     {
    #         "id": row[0],
    #         "sekolah": row[1],
    #         "alamat": row[2],
    #         "kepsek": row[3],
    #         "nip": row[4],
    #         "siswa": row[5],
    #         "nisn": row[6],
    #         "nis": row[7],
    #         "ayah": row[8],
    #         "tempat_lahir": row[9],
    #         "tanggal_lahir": row[10],
    #         "total": row[11],
    #         "terbilang": t.parse(row[11]).getresult()
    #     }
    #     for row in identitas
    # ]
    identitas_list = [
        {
            "id": row[0],
            "sekolah": row[1],
            "alamat": row[2],
            "kepsek": row[3],
            "nip": row[4],
            "siswa": row[5],
            "nisn": row[6],
            "nis": row[7],
            "ayah": row[8],
            "tempat_lahir": row[9],
            "tanggal_lahir": row[10],
            "total": "{{:.{}f}}".format(k).format(row[11] if row[11] is not None else 0.0),
            "terbilang": t.parse("{{:.{}f}}".format(k).format(row[11] if row[11] is not None else 0.0)).getresult()
        }
        for row in identitas
    ]

    # end modified by grey

    return render_template(
        "exam/exam-result-print.html",
        title="Hasil Ujian",
        student_list=student_list,
        school_list=school_list,
        args=args,
        ujian_list=ujian_list,
        exam_id=exam_id,
        now_string=now_string,
        identitas_list=identitas_list,
        hasil_list=hasil_list,
        k=k
    )


@bp.route("/result/<exam_id>/print/<user_id>", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def print_result(exam_id, user_id):

    user = User.query.filter(
        User.id == user_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()
    if user is None:
        abort(404)

    ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
        UjianPeserta.ujian_id == exam_id,
        UjianPeserta.user_id == user_id,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).all()

    return render_template(
        "exam/exam-result-print.html",
    )


@bp.route("/result/<exam_id>/upload", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def upload(exam_id):
    date_format = "%Y/%m/%d %H:%M"
    json_result = {}

    ujian = Ujian.query.filter(Ujian.id == exam_id, Ujian.deleted != True).filter()
    if ujian is None:
        abort(404)

    ujian_sekolah: UjianSekolah = UjianSekolah.query.filter(
        UjianSekolah.ujian_id == exam_id,
        UjianSekolah.sekolah_id == current_user.sekolah_id,
        or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
    ).first()
    if ujian_sekolah is None:
        abort(404)
    json_result["ujian_sekolah"] = {
        "id": ujian_sekolah.id,
        "ujian_id": ujian_sekolah.ujian_id,
        "pelajaran_id": ujian_sekolah.pelajaran_id,
        "jadwal_ujian_id": ujian_sekolah.jadwal_ujian_id,
        "sekolah_id": ujian_sekolah.sekolah_id,
        "status": ujian_sekolah.status,
        "kode": ujian_sekolah.kode,
    }

    ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
        UjianPeserta.ujian_id == exam_id,
        UjianPeserta.sekolah_id == current_user.sekolah_id,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).all()
    json_result["ujian_peserta"] = []
    for i in ujian_peserta:
        json_result["ujian_peserta"].append(
            {
                "id": i.id,
                "user_id": i.user_id,
                "ujian_id": i.ujian_id,
                "pelajaran_id": i.pelajaran_id,
                "jadwal_ujian_id": i.jadwal_ujian_id,
                "sekolah_id": i.sekolah_id,
                "status": i.status,
                "hasil": i.hasil,
                "waktu_mulai": datetime.strftime(i.waktu_mulai, date_format),
                "waktu_selesai": datetime.strftime(i.waktu_selesai, date_format),
            }
        )

    jawaban: list[Jawaban] = Jawaban.query.filter(
        Jawaban.ujian_id == exam_id,
        Jawaban.sekolah_id == current_user.sekolah_id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    )
    json_result["jawaban"] = []
    for i in jawaban:
        json_result["jawaban"].append(
            {
                "id": i.id,
                "user_id": i.user_id,
                "ujian_id": i.ujian_id,
                "pelajaran_id": i.pelajaran_id,
                "jadwal_ujian_id": i.jadwal_ujian_id,
                "sekolah_id": i.sekolah_id,
                "ujian_peserta_id": i.ujian_peserta_id,
                "pertanyaan_id": i.pertanyaan_id,
                "jawaban": i.jawaban,
                "benar": i.benar,
                "nomor": i.nomor,
            }
        )

    r = requests.post(
        environ.get("SERVER_CENTRAL_URL")
        + "/api/upload-result/"
        + exam_id
        + "/"
        + current_user.sekolah_id,
        json=json_result,
    )
    if r is None:
        flash("Terjadi kesalahan saat mengakses server.", "error")
    else:
        flash("Berhasil upload hasil ujian.", "success")

    return redirect(url_for("exam.student_list", exam_id=exam_id))

@bp.route("/download/<exam_id>/lesson", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def download(exam_id):
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()
    # exam_list: list(Ujian) = (
    #     Ujian.query.filter(Ujian.status == "SELESAI", or_(Ujian.deleted.is_(None), Ujian.deleted != True))
    #     .order_by(Ujian.nama.asc())
    #     .all()
    # )
    lesson_list: list(JadwalUjian) = (
        session.query(Ujian.nama.label("ujian"), Pelajaran.id.label("pelajaran_id"), Pelajaran.nama.label("mapel"), JadwalUjian.sesi.label("sesi")).join(Ujian, Ujian.id == JadwalUjian.ujian_id, isouter=False).join(Pelajaran, Pelajaran.id == JadwalUjian.pelajaran_id).filter(JadwalUjian.ujian_id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True, JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True)).all()
    )
    if lesson_list is None:
        abort(404)

    return render_template(
        "exam/exam-download-per-lesson.html",
        title="Download Hasil Ujian",
        exam_id=exam_id,
        lesson_list=lesson_list,
    )

@bp.route("/xlsx/exam/<exam_id>/lesson/<lesson_id>/sesi/<sesi>", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def xlsx(exam_id, lesson_id, sesi):
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()
    
    output = io.BytesIO()
    workbook = xlwt.Workbook()
    sh = workbook.add_sheet("Hasil Ujian")

    sh.write(0, 0, 'No')
    sh.write(0, 1, 'Nama Ujian')
    sh.write(0, 2, 'Mata Pelajaran')
    sh.write(0, 3, 'Sesi')
    sh.write(0, 4, 'NISN')
    sh.write(0, 5, 'Nama Peserta')
    sh.write(0, 6, 'Nilai')

    idx = 0

    hasil_ujian: list(UjianPeserta) = (
        session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), JadwalUjian.sesi.label("sesi"), User.username.label("nisn"), User.nama.label("siswa"), UjianPeserta.hasil.label("nilai")).join(Ujian, UjianPeserta.ujian_id == Ujian.id, isouter=False).join(Pelajaran, UjianPeserta.pelajaran_id == Pelajaran.id, isouter=False).join(User, UjianPeserta.user_id == User.id, isouter=False).join(JadwalUjian, UjianPeserta.jadwal_ujian_id == JadwalUjian.id, isouter=False).filter(UjianPeserta.ujian_id == exam_id, UjianPeserta.pelajaran_id == lesson_id, JadwalUjian.sesi == sesi, UjianPeserta.status == "SELESAI", or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True)).all()
    )
    # hasil_ujian = db.session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), User.username.label("nisn"), User.nama.label("siswa"), UjianPeserta.hasil.label("nilai")).outerjoin(Ujian, Ujian.id == UjianPeserta.ujian_id).outerjoin(Pelajaran, Pelajaran.id == UjianPeserta.pelajaran_id).outerjoin(User, User.id == UjianPeserta.user_id).filter(Ujian.id == exam_id, UjianPeserta.pelajaran_id == lesson_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True, User.deleted.is_(None), User.deleted != True), UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True).all()
    # , or_(Ujian.deleted.is_(None), Ujian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True, User.deleted.is_(None), User.deleted != True), UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True
    if hasil_ujian is None:
        abort(404)

    nomor = 1

    for i in hasil_ujian:
        sh.write(idx+1, 0, nomor)
        sh.write(idx+1, 1, i.ujian)
        sh.write(idx+1, 2, i.mapel)
        sh.write(idx+1, 3, i.sesi)
        sh.write(idx+1, 4, i.nisn)
        sh.write(idx+1, 5, i.siswa)
        sh.write(idx+1, 6, i.nilai)
        idx += 1
        nomor += 1

    workbook.save(output)
    output.seek(0)

    # ujian.nama = session.query(Ujian.nama).filter(Ujian.id == exam_id).first()
    # mapel.nama = session.query(Pelajaran.nama).filter(Pelajaran.id == lesson_id).first()

    mapel: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()

    ujian: Ujian = Ujian.query.filter(
        Ujian.id == exam_id,
        or_(Ujian.deleted.is_(None), Ujian.deleted != True),
    ).first()

    nama_ujian = ujian.nama
    nama_mapel = mapel.nama

    nama_file = nama_ujian + "_" + nama_mapel + "_" + "sesi" + "_" + sesi

    # return render_template(
    #     "exam/debug.html",
    #     title="Download Hasil Ujian",
    #     nama_file=nama_file,
    # )

    return Response(output, mimetype="application/ms-excel", headers={"Content-Disposition":"attachment;filename="+nama_file+".xls"})

@bp.route("/pdf/<exam_id>/<lesson_id>/<sesi>", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def pdf(exam_id, lesson_id, sesi):
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()

    # hasil_ujian: list[UjianPeserta] = (
    #     session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), User.username.label("nisn"), User.nama.label("siswa"), UjianPeserta.hasil.label("nilai")).join(Ujian, UjianPeserta.ujian_id == Ujian.id, isouter=False).join(Pelajaran, UjianPeserta.pelajaran_id == Pelajaran.id, isouter=False).join(User, UjianPeserta.user_id == User.id, isouter=False).filter(Ujian.id == exam_id, UjianPeserta.pelajaran_id == lesson_id).all()
    # )
    # hasil_ujian = session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), User.username.label("nisn"), User.nama.label("siswa"), UjianPeserta.hasil.label("nilai")).join(Ujian, UjianPeserta.ujian_id == Ujian.id, isouter=False).join(Pelajaran, UjianPeserta.pelajaran_id == Pelajaran.id, isouter=False).join(User, UjianPeserta.user_id == User.id, isouter=False).filter(Ujian.id == exam_id, UjianPeserta.pelajaran_id == lesson_id).all()
    hasil_ujian: list(UjianPeserta) = (
        session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), JadwalUjian.sesi.label("sesi"), User.username.label("nisn"), User.nama.label("siswa"), UjianPeserta.hasil.label("nilai")).join(Ujian, UjianPeserta.ujian_id == Ujian.id, isouter=False).join(Pelajaran, UjianPeserta.pelajaran_id == Pelajaran.id, isouter=False).join(User, UjianPeserta.user_id == User.id, isouter=False).join(JadwalUjian, UjianPeserta.jadwal_ujian_id == JadwalUjian.id, isouter=False).filter(UjianPeserta.ujian_id == exam_id, UjianPeserta.pelajaran_id == lesson_id, JadwalUjian.sesi == sesi, UjianPeserta.status == "SELESAI", or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True)).all()
    )
    if hasil_ujian is None:
        abort(404)

    column1Heading = "Ujian"
    column2Heading = "Mata Pelajaran"
    column3Heading = "Sesi"
    column4Heading = "NISN"
    column5Heading = "Siswa"
    column6Heading = "Nilai"

    hasil_ujian_list = [[column1Heading,column2Heading,column3Heading,column4Heading,column5Heading,column6Heading]]

    hasil_ujian_list += [list(i) for i in hasil_ujian]

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    p.drawString(100, 750, "Hasil Ujian")

    # y = 700
    # for i in hasil_ujian:
    #     p.drawString(100, y, f"Ujian: {i['ujian']}")
    #     p.drawString(100, y - 20, f"Mapel: {i['mapel']}")
    #     p.drawString(100, y - 40, f"NISN: {i['nisn']}")
    #     p.drawString(100, y - 60, f"Siswa: {i['siswa']}")
    #     p.drawString(100, y - 80, f"Nilai: {i['nilai']}")
    #     y -= 100

    # p.showPage()
    # p.save()

    # buffer.seek(0)

    mapel: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()

    ujian: Ujian = Ujian.query.filter(
        Ujian.id == exam_id,
        or_(Ujian.deleted.is_(None), Ujian.deleted != True),
    ).first()

    nama_ujian = ujian.nama
    nama_mapel = mapel.nama

    nama_file = nama_ujian + "_" + nama_mapel + "_" + "sesi" + "_" + sesi+".pdf"

    # observe
    # response = Response(mimetype='application/pdf', headers={"Content-Disposition":"attachment;filename=%s.pdf" % (nama_file)})

    data = hasil_ujian_list
    # data = [
    #     ['Dedicated Hosting', 'VPS Hosting', 'Sharing Hosting', 'Reseller Hosting' ],
    #     ['€200/Month', '€100/Month', '€20/Month', '€50/Month'],
    #     ['Free Domain', 'Free Domain', 'Free Domain', 'Free Domain'],
    #     ['2GB DDR2', '20GB Disc Space', 'Unlimited Email', 'Unlimited Email']
    # ]
    doc = SimpleDocTemplate(nama_file, pagesize=letter)
    table = Table(data)

    style = TableStyle([
        ('BACKGROUND', (0,0), (3,0), colors.green),
        ('TEXT_COLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,0), (-1,-1), colors.beige),
    ])

    table.setStyle(style)

    ts = TableStyle([
        ('BOX',(0,0),(-1,-1),2,colors.black),
        ('LINEBEFORE',(2,1),(2,-1),2,colors.red),
        ('LINEABOVE',(0,2),(-1,2),2,colors.green),
        ('GRID',(0,1),(-1,-1),2,colors.black),
        ])

    table.setStyle(ts)

    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading2'], alignment=1, spaceBefore=10, spaceAfter=10)

    elements.append(Paragraph("Hasil Ujian - {nama_ujian}".format(nama_ujian = nama_ujian), title_style))
    elements.append(Paragraph("Mata Pelajaran - {nama_mapel} - Sesi {sesi}".format(nama_mapel = nama_mapel, sesi = sesi), title_style))
    elements.append(table)
    doc.build(elements)
    # return response
    # end observe

    path = "/home/aspd/cbt/"+nama_file

    return send_file(path, as_attachment=True)
    # return Response(mimetype="application/pdf", headers={"Content-Disposition":"attachment;filename=%s" % (nama_file)})
    # return render_template(
    #     "exam/debug.html",
    #     title="Download Hasil Ujian",
    #     data=hasil_ujian_list,
    # )

@bp.route("/review/<ujian_peserta_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def review(ujian_peserta_id):
    filter_sql_jawaban = "j.ujian_peserta_id = '" + ujian_peserta_id + "'"

    sql_jawaban = text(
        """select j.id, p.pertanyaan, p.jawaban as jawaban_benar, p.jumlah_pilihan, p.tipe_pertanyaan, p.pilihan_a, p.pilihan_b, p.pilihan_c, p.pilihan_d, p.pilihan_e, j.jawaban as jawaban_siswa, j.nomor, j.benar as nilai
        from jawaban j
        left join pertanyaan p on j.pertanyaan_id = p.id
        where {} and (p.deleted <> 1 or j.deleted <> 1)""".format(
            filter_sql_jawaban
        )
    )
    result_sql_jawaban = db.engine.execute(sql_jawaban)

    jawaban_list = [
        {
            "id": row[0],
            "pertanyaan": row[1],
            "jawaban_benar": row[2],
            "jumlah_pilihan": row[3],
            "tipe_pertanyaan": row[4],
            "pilihan_a": row[5],
            "pilihan_b": row[6],
            "pilihan_c": row[7],
            "pilihan_d": row[8],
            "pilihan_e": row[9],
            "jawaban_siswa": row[10],
            "nomor": row[11],
            "nilai": row[12],
        }
        for row in result_sql_jawaban
    ]

    return render_template("exam/exam-answer-review.html", title="Review Jawaban", jawaban_list=jawaban_list, ujian_peserta_id=ujian_peserta_id)

@bp.route("/uraian/<exam_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def uraian(exam_id):

    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()

    lesson_list: list(JadwalUjian) = (
        session.query(JadwalUjian.id.label("jadwal_ujian_id"),Ujian.nama.label("ujian"), Pelajaran.id.label("pelajaran_id"), Pelajaran.nama.label("mapel"), JadwalUjian.sesi.label("sesi")).join(Ujian, Ujian.id == JadwalUjian.ujian_id, isouter=False).join(Pelajaran, Pelajaran.id == JadwalUjian.pelajaran_id).filter(JadwalUjian.ujian_id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True, JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True)).all()
    )
    if lesson_list is None:
        abort(404)

    return render_template("exam/exam-essay-mark.html", title="Daftar Ujian", lesson_list=lesson_list)

@bp.route("/uraianresult/<jadwal_ujian_id>/pelajaran/<pelajaran_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def uraianresult(jadwal_ujian_id, pelajaran_id):
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()

    essay_test_result: list(Jawaban) = (
        session.query(Jawaban.id.label("jawaban_id"), User.nama.label("siswa"), Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), JadwalUjian.id.label("jadwal_ujian_id"), UjianPeserta.id.label("ujian_peserta_id"), Pertanyaan.pertanyaan.label("pertanyaan"), Jawaban.jawaban.label("jawaban"), Jawaban.benar.label("benar"), Jawaban.nomor.label("nomor")).join(Pertanyaan, Pertanyaan.id == Jawaban.pertanyaan_id, isouter=False).join(User, User.id == Jawaban.user_id, isouter=False).join(Ujian, Ujian.id == Jawaban.ujian_id, isouter=False).join(JadwalUjian, JadwalUjian.id == Jawaban.jadwal_ujian_id, isouter=False).join(UjianPeserta, UjianPeserta.id == Jawaban.ujian_peserta_id, isouter=False).join(Pelajaran, Pelajaran.id == Jawaban.pelajaran_id, isouter=False).filter(Jawaban.jadwal_ujian_id == jadwal_ujian_id, Jawaban.pelajaran_id == pelajaran_id, Pertanyaan.tipe_pertanyaan == "uraian", or_(Ujian.deleted.is_(None), Ujian.deleted != True, JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True, Jawaban.deleted.is_(None), Jawaban.deleted != True)).all()
    )
    if essay_test_result is None:
        abort(404)

    return render_template("exam/exam-essay-test-result.html", title="Hasil Ujian Uraian", essay_test_result=essay_test_result)