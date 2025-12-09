import datetime
import random
import string
import sqlalchemy
from urllib.request import urlopen

from app import db
from app.decorators import role_required
from app.models import (
    JadwalUjian,
    Jawaban,
    Pelajaran,
    PelajaranUjian,
    Pertanyaan,
    Sekolah,
    Ujian,
    UjianPeserta,
    UjianSekolah,
    User,
    RombonganBelajar
)
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, text, create_engine
from sqlalchemy.orm import sessionmaker

bp = Blueprint("schedule", __name__)


@bp.route("/<exam_id>/list", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def show(exam_id):
    exam = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    schedule: list[JadwalUjian] = (
        JadwalUjian.query.filter(
            JadwalUjian.ujian_id == exam_id,
            or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
        )
        .order_by(JadwalUjian.ujian_id.asc(), JadwalUjian.sesi.asc())
        .all()
    )

    schedule_list = []
    if current_user.role == "proktor":
        for i in schedule:
            ujian_sekolah = UjianSekolah.query.filter(
                UjianSekolah.jadwal_ujian_id == i.id,
                UjianSekolah.sekolah_id == current_user.sekolah_id,
                or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
            ).first()

            if ujian_sekolah is None:
                ujian_sekolah = UjianSekolah(
                    ujian_id=i.ujian_id,
                    pelajaran_id=i.pelajaran_id,
                    jadwal_ujian_id=i.id,
                    sekolah_id=current_user.sekolah_id,
                    status="BARU",
                    kode="",
                )
                db.session.add(ujian_sekolah)
                db.session.commit()

            pelajaran: Pelajaran = Pelajaran.query.filter(
                Pelajaran.id == i.pelajaran_id
            ).first()

            schedule_list.append(
                {
                    "id": i.id,
                    "ujian_id": i.ujian_id,
                    "pelajaran_id": i.pelajaran_id,
                    "pelajaran": {
                        "kode": pelajaran.kode,
                        "nama": pelajaran.nama,
                    },
                    "sesi": i.sesi,
                    "tanggal": i.tanggal,
                    "durasi": i.durasi,
                    "created_at": i.created_at,
                    "status": ujian_sekolah.status,
                    "kode": ujian_sekolah.kode,
                }
            )
    else:
        schedule_list = schedule

    return render_template(
        "exam/exam-schedule-list.html",
        title="Jadwal Ujian",
        schedule_list=schedule_list,
        exam=exam,
    )


@bp.route("/add/<exam_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def add(exam_id):

    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    form = {}
    errors = []

    if request.method == "POST":
        form = {}
        pelajaran = request.form.get("pelajaran", default="", type=str)
        sesi = request.form.get("sesi", default="", type=str)
        tanggal = request.form.get("tanggal", default="", type=str)
        waktu = request.form.get("waktu", default="", type=str)
        durasi = request.form.get("durasi", default=None, type=int)

        form = {
            "pelajaran": pelajaran,
            "sesi": sesi,
            "tanggal": tanggal,
            "waktu": waktu,
            "durasi": durasi,
        }

        if pelajaran == "":
            errors.append("Pelajaran tidak boleh kosong.")

        if sesi == "":
            errors.append("Sesi tidak boleh kosong.")

        if tanggal == "":
            errors.append("Tanggal tidak boleh kosong.")
        else:
            try:
                datetime.datetime.strptime(tanggal, "%m/%d/%Y")
            except Exception:
                errors.append("Format tanggal tidak sesuai.")

        if waktu == "":
            errors.append("Waktu tidak boleh kosong.")
        else:
            try:
                datetime.datetime.strptime(waktu, "%H:%M")
            except Exception:
                errors.append("Format waktu tidak sesuai.")

        if durasi is None:
            errors.append("Durasi tidak boleh kosong.")

        if len(errors) == 0:
            jadwal_ujian = JadwalUjian()
            jadwal_ujian.ujian_id = exam.id
            jadwal_ujian.pelajaran_id = pelajaran
            jadwal_ujian.sesi = sesi
            jadwal_ujian.tanggal = datetime.datetime.strptime(
                "{} {}".format(tanggal, waktu), "%m/%d/%Y %H:%M"
            )
            jadwal_ujian.durasi = durasi

            db.session.add(jadwal_ujian)
            db.session.commit()
            flash("Berhasil menyimpan jadwal ujian.", "success")
            return redirect(url_for("exam.schedule.show", exam_id=exam.id))
        else:
            flash("\\n".join(errors), "error")

    lesson_list = PelajaranUjian.query.filter(
        PelajaranUjian.ujian_id == exam_id,
        or_(PelajaranUjian.deleted.is_(None), PelajaranUjian.deleted != True),
    ).all()

    return render_template(
        "exam/exam-schedule-form.html",
        title="Tambah Ujian",
        form=form,
        id=None,
        lesson_list=lesson_list,
        exam=exam,
    )


@bp.route("/edit/<exam_id>/edit/<schedule_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def edit(exam_id, schedule_id):
    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    schedule: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == schedule_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if schedule is None:
        abort(404)

    form = {}
    form["pelajaran"] = schedule.pelajaran_id
    form["sesi"] = schedule.sesi
    form["tanggal"] = datetime.datetime.strftime(schedule.tanggal, "%m/%d/%Y")
    form["waktu"] = datetime.datetime.strftime(schedule.tanggal, "%H:%M")
    form["durasi"] = schedule.durasi

    errors = []

    if request.method == "POST":
        form = {}
        pelajaran = request.form.get("pelajaran", default="", type=str)
        sesi = request.form.get("sesi", default="", type=str)
        tanggal = request.form.get("tanggal", default="", type=str)
        waktu = request.form.get("waktu", default="", type=str)
        durasi = request.form.get("durasi", default=None, type=int)

        form = {
            "pelajaran": pelajaran,
            "sesi": sesi,
            "tanggal": tanggal,
            "waktu": waktu,
            "durasi": durasi,
        }

        if pelajaran == "":
            errors.append("Pelajaran tidak boleh kosong.")

        if sesi == "":
            errors.append("Sesi tidak boleh kosong.")

        if tanggal == "":
            errors.append("Tanggal tidak boleh kosong.")
        else:
            try:
                datetime.datetime.strptime(tanggal, "%m/%d/%Y")
            except Exception:
                errors.append("Format tanggal tidak sesuai.")

        if waktu == "":
            errors.append("Waktu tidak boleh kosong.")
        else:
            try:
                datetime.datetime.strptime(waktu, "%H:%M")
            except Exception:
                errors.append("Format waktu tidak sesuai.")

        if durasi is None:
            errors.append("Durasi tidak boleh kosong.")

        if len(errors) == 0:
            schedule.ujian_id = exam.id
            schedule.pelajaran_id = pelajaran
            schedule.sesi = sesi
            schedule.tanggal = datetime.datetime.strptime(
                "{} {}".format(tanggal, waktu), "%m/%d/%Y %H:%M"
            )
            schedule.durasi = durasi

            db.session.commit()
            flash("Berhasil menyimpan jadwal ujian.", "success")
            return redirect(url_for("exam.schedule.show", exam_id=exam.id))
        else:
            flash("\\n".join(errors), "error")

    lesson_list = PelajaranUjian.query.filter(
        PelajaranUjian.ujian_id == exam_id,
        or_(PelajaranUjian.deleted.is_(None), PelajaranUjian.deleted != True),
    ).all()

    return render_template(
        "exam/exam-schedule-form.html",
        title="Edit Ujian",
        form=form,
        id=id,
        lesson_list=lesson_list,
        exam=exam,
    )


@bp.route("/<exam_id>/delete/<schedule_id>", methods=["GET"])
@login_required
@role_required(roles=["admin"])
def delete(exam_id, schedule_id):
    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    schedule: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == schedule_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if schedule is None:
        abort(404)

    schedule.deleted = True
    # db.session.delete(schedule)
    db.session.commit()

    flash("Sukses menghapus jadwal ujian.", "success")

    return redirect(url_for("exam.schedule.show", exam_id=exam.id))


@bp.route("/<exam_id>/start/<schedule_id>", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def start(exam_id, schedule_id):
    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    schedule: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == schedule_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if schedule is None:
        abort(404)

    now = datetime.datetime.now()
    if now < schedule.tanggal - datetime.timedelta(minutes=30):
        flash("Ujian belum bisa dimulai.", "error")
        return redirect(url_for("exam.schedule.show", exam_id=exam_id))
    elif now > schedule.tanggal + datetime.timedelta(minutes=schedule.durasi):
        flash("Ujian sudah selesai (melebihi waktu dapat dimulai).", "error")
        return redirect(url_for("exam.schedule.show", exam_id=exam_id))

    ujian_sekolah: UjianSekolah = UjianSekolah.query.filter(
        UjianSekolah.jadwal_ujian_id == schedule_id,
        UjianSekolah.sekolah_id == current_user.sekolah_id,
        or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
    ).first()
    if ujian_sekolah is None:
        abort(404)

    ujian_sekolah.status = "BERJALAN"
    ujian_sekolah.kode = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=5)
    )

    db.session.commit()

    return redirect(url_for("exam.schedule.show", exam_id=exam_id))


@bp.route("/<exam_id>/stop/<schedule_id>", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def stop(exam_id, schedule_id):
    exam: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if exam is None:
        abort(404)

    schedule: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == schedule_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if schedule is None:
        abort(404)

    ujian_sekolah: UjianSekolah = UjianSekolah.query.filter(
        UjianSekolah.jadwal_ujian_id == schedule_id,
        UjianSekolah.sekolah_id == current_user.sekolah_id,
        or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
    ).first()
    if ujian_sekolah is None:
        abort(404)

    ujian_sekolah.status = "SELESAI"
    ujian_sekolah.kode = ""

    db.session.commit()

    return redirect(url_for("exam.schedule.show", exam_id=exam_id))


#modified
@bp.route("/<exam_id>/student/<schedule_id>/lesson/<lesson_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "proktor"])
def student_list(exam_id, schedule_id, lesson_id):
#modified

    school = request.args.get("school", default="", type=str)

    args = request.args

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    student_list = []

    if school != "":
        filter = [
            UjianPeserta.jadwal_ujian_id == schedule_id,
            UjianPeserta.sekolah_id == school,
            or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
        ]

        student_list = UjianPeserta.query.filter(*filter).all()

    school_list = (
        Sekolah.query.filter(or_(Sekolah.deleted.is_(None), Sekolah.deleted != True))
        .order_by(Sekolah.nama.asc())
        .all()
    )

    # exam: JadwalUjian = JadwalUjian.query.filter(
    #     JadwalUjian.id == schedule_id,
    #     JadwalUjian.ujian_id == exam_id,
    #     or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    # ).join(Ujian, Ujian.id == JadwalUjian.ujian_id, isouter=False).first()
    # if exam is None:
    #     abort(404)

    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/tka')
    Session = sessionmaker(bind = engine)
    session = Session()

    exam: list(JadwalUjian) = (
        session.query(Ujian.nama.label("ujian"), Pelajaran.nama.label("mapel"), JadwalUjian.sesi.label("sesi")).join(Ujian, Ujian.id == JadwalUjian.ujian_id, isouter=False).join(Pelajaran, Pelajaran.id == JadwalUjian.pelajaran_id).filter(JadwalUjian.ujian_id == exam_id, JadwalUjian.id == schedule_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True, JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True, Pelajaran.deleted.is_(None), Pelajaran.deleted != True)).first()
    )
    if exam is None:
        abort(404)

    return render_template(
        "exam/exam-student-list.html",
        title="Peserta",
        student_list=student_list,
        school_list=school_list,
        args=args,
        exam_id=exam_id,
        schedule_id=schedule_id,
        lesson_id=lesson_id,
        exam=exam,
    )


@bp.route("/<exam_id>/student/<schedule_id>/add/lesson/<lesson_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "proktor"])
def student_add(exam_id, schedule_id, lesson_id):
    school = request.args.get("school", default="", type=str)

    ujian: Ujian = Ujian.query.filter(
        Ujian.id == exam_id, or_(Ujian.deleted.is_(None), Ujian.deleted != True)
    ).first()
    if ujian is None:
        abort(404)

    jadwal_ujian: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == schedule_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if jadwal_ujian is None:
        abort(404)

    args = request.args
    form = {}
    form["peserta"] = []

    if current_user.role == "proktor":
        school = current_user.sekolah_id
        args = {"school": school}

    ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
        UjianPeserta.ujian_id == exam_id,
        UjianPeserta.jadwal_ujian_id == schedule_id,
        UjianPeserta.sekolah_id == school,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).all()
    for i in ujian_peserta:
        form["peserta"].append(i.user_id)

    if request.method == "POST":
        peserta = request.form.getlist("peserta")
        form["peserta"] = peserta

        # modified
        filter_ujian_check_exists = "up.pelajaran_id = '" + lesson_id + "'" + "and up.jadwal_ujian_id = '" + schedule_id + "'"
        check_exists_query = text(
            """select up.user_id, up.sekolah_id, up.jadwal_ujian_id, up.ujian_id, up.pelajaran_id
            from ujian_peserta up
            where {} and up.deleted != 1""".format(
                filter_ujian_check_exists
            )
        )

        result_check_exists_query = db.engine.execute(check_exists_query)

        for row in result_check_exists_query:
            if row.user_id in peserta:
                if row.jadwal_ujian_id == schedule_id:
                    continue

        filter_ujian_check_if_registrated_in_other_session = "up.pelajaran_id = '" + lesson_id + "'" + "and up.ujian_id = '" + exam_id + "'" + "and up.jadwal_ujian_id != '" + schedule_id + "'"
        check_if_registrated_in_other_session_query = text(
            """select up.user_id, up.sekolah_id, up.jadwal_ujian_id, up.ujian_id, up.pelajaran_id
            from ujian_peserta up
            where {} and up.deleted != 1""".format(
                filter_ujian_check_if_registrated_in_other_session
            )
        )

        result_check_if_registrated_in_other_session_query = db.engine.execute(check_if_registrated_in_other_session_query)

        for row in result_check_if_registrated_in_other_session_query:
            if row.user_id in peserta:
                flash("User telah terdaftar di sesi lain!", "error")
                return redirect(url_for("exam.schedule.student_list", exam_id=exam_id, schedule_id=schedule_id, lesson_id=lesson_id))
        # modified

        ujian_peserta: list[UjianPeserta] = UjianPeserta.query.filter(
            UjianPeserta.ujian_id == exam_id,
            UjianPeserta.sekolah_id == school,
            UjianPeserta.jadwal_ujian_id == schedule_id,
        ).all()

        for i in ujian_peserta:
            if i.user_id not in peserta:
                i.deleted = True
            else:
                i.deleted = False
                peserta.remove(i.user_id)
                
        for i in peserta:
            up = UjianPeserta()
            up.user_id = i
            up.pelajaran_id = jadwal_ujian.pelajaran_id
            up.ujian_id = exam_id
            up.jadwal_ujian_id = schedule_id
            up.sekolah_id = school
            db.session.add(up)

        db.session.commit()

        return redirect(
            url_for(
                "exam.schedule.student_list", exam_id=exam_id, schedule_id=schedule_id, lesson_id=lesson_id,
            )
        )

    student_list = (
        User.query.filter(
            User.sekolah_id == school,
            User.role == "peserta_didik",
            or_(User.deleted.is_(None), User.deleted != True),
        )
        .order_by(User.username.asc())
        .all()
    )

    rombel_list = RombonganBelajar.query.with_entities(RombonganBelajar.id, RombonganBelajar.tingkat_pendidikan, RombonganBelajar.nama).order_by(RombonganBelajar.nama.asc()).all()

    return render_template(
        "exam/exam-student-form.html",
        title="Peserta",
        student_list=student_list,
        rombel_list=rombel_list,
        args=args,
        form=form,
        lesson_id=lesson_id,
    )


@bp.route("/<exam_id>/student/<schedule_id>/end/<user_id>/lesson/<lesson_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["proktor", "admin"])
def end(exam_id, schedule_id, user_id, lesson_id):
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == user_id,
        UjianPeserta.status == "BERJALAN",
        UjianPeserta.ujian_id == exam_id,
        UjianPeserta.jadwal_ujian_id == schedule_id,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    ujian_peserta.waktu_selesai = datetime.datetime.now()
    ujian_peserta.status = "SELESAI"

    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()
    jawaban_benar = Jawaban.query.filter(
        Jawaban.ujian_peserta_id == ujian_peserta.id,
        Jawaban.benar == True,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).count()
    ujian_peserta.hasil = jawaban_benar / jumlah_soal * 100

    db.session.commit()

    flash("Ujian telah selesai.", "success")
    return redirect(
        url_for("exam.schedule.student_list", exam_id=exam_id, schedule_id=schedule_id, lesson_id=lesson_id)
    )

# modified by jamhari
# reset ujian peserta tanpa mengurangi waktu ujian  
@bp.route("/<exam_id>/student/<schedule_id>/reset/<user_id>/lesson/<lesson_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["proktor", "admin"])
def reset(exam_id, schedule_id, user_id, lesson_id):
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == user_id,
        UjianPeserta.status.in_(["BERJALAN", "SELESAI"]),
        UjianPeserta.ujian_id == exam_id,
        UjianPeserta.jadwal_ujian_id == schedule_id,
        UjianPeserta.waktu_mulai != None,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    ujian_peserta_id = ujian_peserta.id

    ujian_peserta.hasil = None
    ujian_peserta.waktu_mulai = None
    ujian_peserta.waktu_selesai = None
    ujian_peserta.updated_at = None
    ujian_peserta.status = "BARU"

    db.session.commit()

    jawaban: Jawaban = Jawaban.query.filter(
        Jawaban.ujian_peserta_id == ujian_peserta_id
    ).all()
    if jawaban is None:
        abort(404)

    for i in jawaban:
        i.deleted = 1

    db.session.commit()

    flash("Status ujian peserta telah direset.", "success")
    return redirect(
        url_for("exam.schedule.student_list", exam_id=exam_id, schedule_id=schedule_id, lesson_id=lesson_id)
    )


# jika ingin mengurangi waktu ujian saat reset, gunakan kode di bawah ini sebagai pengganti kode di atas
# modified  by jamhari 

# @bp.route("/<exam_id>/student/<schedule_id>/reset/<user_id>/lesson/<lesson_id>", methods=["GET", "POST"])
# @login_required
# @role_required(roles=["proktor", "admin"])
# def reset(exam_id, schedule_id, user_id, lesson_id):
#     # 1. Ambil data peserta ujian
#     ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
#         UjianPeserta.user_id == user_id,
#         UjianPeserta.status.in_(["BERJALAN", "SELESAI", "BARU"]), # Tambahkan BARU untuk jaga-jaga
#         UjianPeserta.ujian_id == exam_id,
#         UjianPeserta.jadwal_ujian_id == schedule_id,
#         # UjianPeserta.waktu_mulai != None, # Dihapus agar query lebih fleksibel, dicek di logic bawah
#         or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#     ).first()

#     if ujian_peserta is None:
#         abort(404)

#     # --- [MODIFIKASI MULAI] LOGIKA PENGURANGAN WAKTU ---
#     if ujian_peserta.waktu_mulai is not None:
#         # Ambil durasi total ujian dari JadwalUjian untuk referensi
#         jadwal = JadwalUjian.query.filter(JadwalUjian.id == schedule_id).first()
#         durasi_total_detik = jadwal.durasi * 60 if jadwal else 0
        
#         # Hitung berapa lama siswa sudah mengerjakan (Waktu Sekarang - Waktu Mulai)
#         waktu_sekarang = datetime.datetime.now()
#         delta_terpakai = waktu_sekarang - ujian_peserta.waktu_mulai
#         detik_terpakai = delta_terpakai.total_seconds()

#         # Tentukan sisa waktu sebelumnya
#         # Jika sisa_waktu di DB masih None, berarti masih punya waktu full (durasi jadwal)
#         sisa_sebelumnya = ujian_peserta.sisa_waktu if ujian_peserta.sisa_waktu is not None else durasi_total_detik
        
#         # Kurangi sisa waktu
#         sisa_baru = sisa_sebelumnya - detik_terpakai
        
#         # Update ke database (Pastikan tidak minus)
#         ujian_peserta.sisa_waktu = max(0, sisa_baru)
#     # --- [MODIFIKASI SELESAI] ---

#     ujian_peserta_id = ujian_peserta.id

#     # Reset atribut lainnya
#     ujian_peserta.hasil = None
#     ujian_peserta.waktu_mulai = None # Waktu mulai dikosongkan agar timer client mulai menghitung dari sisa_waktu
#     ujian_peserta.waktu_selesai = None
#     ujian_peserta.updated_at = None
#     ujian_peserta.status = "BARU" # Status dikembalikan ke BARU agar bisa login lagi

#     # Simpan perubahan UjianPeserta
#     db.session.commit()

#     # Hapus jawaban (sesuai kode asli Anda)
#     jawaban: Jawaban = Jawaban.query.filter(
#         Jawaban.ujian_peserta_id == ujian_peserta_id
#     ).all()
    
#     # Perbaikan loop delete agar lebih aman jika jawaban kosong
#     if jawaban:
#         for i in jawaban:
#             i.deleted = 1
#         db.session.commit()

#     flash("Status ujian peserta telah direset dan waktu telah dikurangi.", "success")
#     return redirect(
#         url_for("exam.schedule.student_list", exam_id=exam_id, schedule_id=schedule_id, lesson_id=lesson_id)
#     )