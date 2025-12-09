import datetime
from operator import or_
import random

from app import db, csrf
from app.decorators import redirect_exam, role_required
from app.models import (
    JadwalUjian,
    Jawaban,
    Pelajaran,
    Pertanyaan,
    UjianPeserta,
    UjianSekolah,
)
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import text

bp = Blueprint("doing", __name__)

@bp.route("/get-code", methods=["GET", "POST"])
@login_required
@redirect_exam
def code():
    errors = []
    form = {}

    if request.method == "POST":
        kode = request.form.get("kode")

        if kode is None or kode == "":
            flash("Kode tidak boleh kosong", "error")
        else:
            ujian_sekolah: UjianSekolah = UjianSekolah.query.filter_by(
                kode=kode
            ).first()
            if ujian_sekolah is None:
                flash("Kode tidak ditemukan.", "error")
            else:
                ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
                    UjianPeserta.jadwal_ujian_id == ujian_sekolah.jadwal_ujian_id,
                    UjianPeserta.user_id == current_user.id,
                    or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
                ).first()

                if ujian_peserta is None:
                    flash("Anda tidak terdaftar di ujian ini", "error")
                else:
                    if ujian_peserta.status == "SELESAI":
                        flash("Anda telah melakukan ujian.", "error")
                    else:
                        return redirect(url_for("doing.confirm", kode_ujian=kode))

    return render_template(
        "doing/code.html",
        title="Ujian",
        exam_student={},
        errors=errors,
        form=form,
    )


@bp.route("/confirm/<kode_ujian>", methods=["GET", "POST"])
@login_required
@redirect_exam
def confirm(kode_ujian):
    errors = []
    form = {}

    ujian_sekolah: UjianSekolah = UjianSekolah.query.filter(
        UjianSekolah.kode == kode_ujian,
        or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
    ).first()
    if ujian_sekolah is None:
        flash("Kode tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    pelajaran: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == ujian_sekolah.pelajaran_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if pelajaran is None:
        flash("Pelajaran tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    jadwal_ujian: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == ujian_sekolah.jadwal_ujian_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if jadwal_ujian is None:
        flash("Jadwal Ujian tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    return render_template(
        "doing/confirm.html",
        title="Konfirmasi",
        ujian_sekolah=ujian_sekolah,
        pelajaran=pelajaran,
        jadwal_ujian=jadwal_ujian,
        errors=errors,
        form=form,
        kode_ujian=kode_ujian,
    )


@bp.route("/start/<kode_ujian>", methods=["GET", "POST"])
@login_required
@redirect_exam
def start(kode_ujian):
    ujian_sekolah: UjianSekolah = UjianSekolah.query.filter(
        UjianSekolah.kode == kode_ujian,
        or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True),
    ).first()
    if ujian_sekolah is None:
        flash("Kode tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    jadwal_ujian: JadwalUjian = JadwalUjian.query.filter(
        JadwalUjian.id == ujian_sekolah.jadwal_ujian_id,
        or_(JadwalUjian.deleted.is_(None), JadwalUjian.deleted != True),
    ).first()
    if jadwal_ujian is None:
        flash("Jadwal Ujian tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    pelajaran: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == ujian_sekolah.pelajaran_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if pelajaran is None:
        flash("Pelajaran tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == pelajaran.id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).all()
    if len(pelajaran.pertanyaan) == 0:
        flash("Pertanyaan tidak ditemukan.", "error")
        return redirect(url_for("doing.code"))

    ujian_peserta = UjianPeserta.query.filter(
        UjianPeserta.jadwal_ujian_id == jadwal_ujian.id,
        UjianPeserta.user_id == current_user.id,
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is not None:
        db.session.delete(ujian_peserta)

    jawaban: list[Jawaban] = Jawaban.query.filter(
        Jawaban.jadwal_ujian_id == jadwal_ujian.id,
        Jawaban.user_id == current_user.id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).all()
    for i in jawaban:
        db.session.delete(i)

    db.session.flush()

    ujian_peserta = UjianPeserta(
        user_id=current_user.id,
        ujian_id=ujian_sekolah.ujian_id,
        pelajaran_id=pelajaran.id,
        jadwal_ujian_id=jadwal_ujian.id,
        sekolah_id=current_user.sekolah_id,
        status="BERJALAN",
        hasil=None,
        waktu_mulai=datetime.datetime.now(),
        waktu_selesai=None,
    )
    db.session.add(ujian_peserta)
    db.session.flush()

    random.shuffle(pertanyaan)
    for index, value in enumerate(pertanyaan):
        jawaban = Jawaban(
            user_id=current_user.id,
            ujian_id=ujian_sekolah.ujian_id,
            pelajaran_id=pelajaran.id,
            jadwal_ujian_id=jadwal_ujian.id,
            sekolah_id=current_user.sekolah_id,
            ujian_peserta_id=ujian_peserta.id,
            pertanyaan_id=value.id,
            jawaban=None,
            benar=False,
            nomor=index + 1,
        )
        db.session.add(jawaban)

    db.session.commit()

    return redirect(url_for("doing.action", number=1))


@bp.route("/action/<number>", methods=["GET"])
@login_required
def action(number=1):
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    jawaban: Jawaban = Jawaban.query.filter(
        Jawaban.user_id == current_user.id,
        Jawaban.nomor == number,
        Jawaban.ujian_peserta_id == ujian_peserta.id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).first()
    if jawaban is None:
        abort(404)

    pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == jawaban.pertanyaan_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if pertanyaan is None:
        abort(404)

    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == jawaban.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()

    answer_list = (
        Jawaban.query.filter(
            Jawaban.ujian_peserta_id == ujian_peserta.id,
            or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
        )
        .order_by(Jawaban.nomor.asc())
        .all()
    )

    return render_template(
        "doing/action.html",
        title="Ujian",
        jawaban=jawaban,
        pertanyaan=pertanyaan,
        jumlah_soal=jumlah_soal,
        answer_list=answer_list,
        ujian_peserta=ujian_peserta,
    )


# @bp.route("/answer/<number>/<opt>", methods=["GET"])
# @login_required
# def answer(number, opt):
#     ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
#         UjianPeserta.user_id == current_user.id,
#         UjianPeserta.status == "BERJALAN",
#         or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#     ).first()
#     if ujian_peserta is None:
#         abort(404)

#     answer: Jawaban = Jawaban.query.filter(
#         Jawaban.nomor == number,
#         Jawaban.ujian_peserta_id == ujian_peserta.id,
#         or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
#     ).first()
#     if answer is None:
#         abort(404)

#     pertanyaan: Pertanyaan = Pertanyaan.query.filter(
#         Pertanyaan.id == answer.pertanyaan_id,
#         or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
#     ).first()
#     if pertanyaan is None:
#         abort(404)

#     answer.jawaban = opt

#     answer.benar = pertanyaan.jawaban == opt
#     db.session.commit()

#     jumlah_soal = Pertanyaan.query.filter(
#         Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
#         or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
#     ).count()

#     if (int(number) + 1) > jumlah_soal:
#         return redirect(url_for("doing.action", number=1))

#     return redirect(url_for("doing.action", number=int(number) + 1))
# @bp.route("/answer", methods=["GET", "POST"])
# @login_required
# @csrf.exempt
# def answer():
#     if request.method == "POST":
#         ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
#             UjianPeserta.user_id == current_user.id,
#             UjianPeserta.status == "BERJALAN",
#             or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#         ).first()
#         if ujian_peserta is None:
#             abort(404)

#         number = request.form.get("number")
#         if number is None:
#             abort(404)

#         answer: Jawaban = Jawaban.query.filter(
#             Jawaban.nomor == number,
#             Jawaban.ujian_peserta_id == ujian_peserta.id,
#             or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
#             ).first()
#         if answer is None:
#             abort(404)

#         pertanyaan: Pertanyaan = Pertanyaan.query.filter(
#             Pertanyaan.id == answer.pertanyaan_id,
#             or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
#         ).first()
#         if pertanyaan is None:
#             abort(404)

#         next_dir = request.form.get("next")
#         prev_dir = request.form.get("previous")
#         pilgan = request.form.get("jawaban")
#         uraian = request.form.get("jawaban_uraian")

#         if pilgan is not None:
#             opt = request.form.get("jawaban")

#             answer.jawaban = opt

#             answer.benar = pertanyaan.jawaban == opt

#             db.session.commit()

#         if uraian is not None:
#             jawaban_uraian = request.form.get("jawaban_uraian")

#             answer.jawaban = jawaban_uraian if jawaban_uraian != "" else None

#             db.session.commit()

#     jumlah_soal = Pertanyaan.query.filter(
#         Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
#         or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
#     ).count()

#     if next_dir is not None:
#         if (int(number) + 1) > jumlah_soal:
#             return redirect(url_for("doing.action", number=1))
#         else:
#             return redirect(url_for("doing.action", number=int(number) + 1))
#     if prev_dir is not None:
#         if (int(number) - 1) <= 0:
#             return redirect(url_for("doing.action", number=int(jumlah_soal)))
#         else:
#             return redirect(url_for("doing.action", number=int(number) - 1))

@bp.route("/answer/<number>/<opt>", methods=["GET"])
@login_required
def answer(number, opt):
    # 1. Cari data peserta ujian yang sedang berjalan
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    
    if ujian_peserta is None:
        abort(404)

    # 2. Cari data jawaban berdasarkan nomor soal
    answer: Jawaban = Jawaban.query.filter(
        Jawaban.nomor == number,
        Jawaban.ujian_peserta_id == ujian_peserta.id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).first()
    
    if answer is None:
        abort(404)

    # 3. Cari data pertanyaan asli untuk kunci jawaban
    pertanyaan: Pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == answer.pertanyaan_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    
    if pertanyaan is None:
        abort(404)

    # 4. Simpan Jawaban Siswa
    answer.jawaban = opt
    # Cek kebenaran jawaban (untuk scoring otomatis)
    answer.benar = (pertanyaan.jawaban == opt)
    
    db.session.commit()

    # 5. Hitung total soal untuk navigasi
    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()

    # 6. Redirect ke soal berikutnya (atau kembali ke no 1 jika sudah habis)
    if (int(number) + 1) > jumlah_soal:
        return redirect(url_for("doing.action", number=1))

    return redirect(url_for("doing.action", number=int(number) + 1))

@bp.route("/answer_checklist/<number>", methods=["POST"])
@login_required
def answer_checklist(number):
    """Menerima jawaban checklist (beberapa pilihan). Menyimpan sebagai string terurut
    misal 'A,C' dan menandai benar hanya jika set jawaban siswa sama persis dengan kunci.
    """
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    answer: Jawaban = Jawaban.query.filter(
        Jawaban.nomor == number,
        Jawaban.ujian_peserta_id == ujian_peserta.id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).first()
    if answer is None:
        abort(404)

    pertanyaan: Pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == answer.pertanyaan_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if pertanyaan is None:
        abort(404)

    # Ambil daftar pilihan yang dipilih siswa
    selected = request.form.getlist('opt')

    if not selected:
        # Tidak memilih apapun
        answer.jawaban = None
        answer.benar = False
    else:
        # Normalisasi: uppercase, hapus spasi, urutkan
        selected_norm = [s.strip().upper() for s in selected if s and s.strip()]
        selected_norm = sorted(set(selected_norm))
        answer_str = ",".join(selected_norm)
        answer.jawaban = answer_str

        # Ambil kunci jawaban dari pertanyaan, bisa berupa 'A' atau 'A,C'
        if pertanyaan.jawaban:
            key_list = [k.strip().upper() for k in pertanyaan.jawaban.split(',') if k.strip()]
            key_set = set(key_list)
        else:
            key_set = set()

        student_set = set(selected_norm)

        # Menilai: benar hanya jika set siswa sama persis dengan set kunci
        answer.benar = (student_set == key_set)

    db.session.commit()

    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()

    if (int(number) + 1) > jumlah_soal:
        return redirect(url_for("doing.action", number=1))

    return redirect(url_for("doing.action", number=int(number) + 1))


@bp.route("/answer_benar_salah/<number>", methods=["POST"])
@login_required
def answer_benar_salah(number):
    """Menerima jawaban Benar-Salah / Sesuai-Tidak Sesuai.
    Menyimpan sebagai string terurut misal 'A,B,A'.
    """
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    answer: Jawaban = Jawaban.query.filter(
        Jawaban.nomor == number,
        Jawaban.ujian_peserta_id == ujian_peserta.id,
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
    ).first()
    if answer is None:
        abort(404)

    pertanyaan: Pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == answer.pertanyaan_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if pertanyaan is None:
        abort(404)

    # Ambil 3 jawaban: 'A' (Sesuai/Benar) atau 'B' (Tidak Sesuai/Salah)
    ans1 = request.form.get('answer_1') 
    ans2 = request.form.get('answer_2') 
    ans3 = request.form.get('answer_3') 
    
    selected_answers = [ans1, ans2, ans3]
    
    if None in selected_answers:
        # Jika ada yang belum dijawab, simpan None dan False
        answer.jawaban = None
        answer.benar = False
    else:
        # Gabungkan menjadi string, misal 'A,B,A'
        answer_str = ",".join(selected_answers)
        answer.jawaban = answer_str

        # Ambil kunci jawaban dari pertanyaan, misal 'A,B,A'
        key_str = pertanyaan.jawaban if pertanyaan.jawaban else ""
        
        # Menilai: benar hanya jika string siswa sama persis dengan string kunci
        answer.benar = (answer_str == key_str)

    db.session.commit()

    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()

    if (int(number) + 1) > jumlah_soal:
        return redirect(url_for("doing.action", number=1))

    return redirect(url_for("doing.action", number=int(number) + 1))

@bp.route("/list", methods=["GET"])
@login_required
def list():
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    answer_list = (
        Jawaban.query.filter(
            Jawaban.ujian_peserta_id == ujian_peserta.id,
            or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
        )
        .first()
        .order_by(Jawaban.nomor.asc())
        .all()
    )

    return render_template(
        "doing/question-list.html",
        title="Daftar Soal",
        exam_student=ujian_peserta,
        answer_list=answer_list,
    )

### kode lama hanya soal piliahan ganda yang di nilai otomatis 
# @bp.route("/end", methods=["GET", "POST"])
# @login_required
# def end():
#     ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
#         UjianPeserta.user_id == current_user.id,
#         UjianPeserta.status == "BERJALAN",
#         or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#     ).first()
#     if ujian_peserta is None:
#         abort(404)

#     ujian_peserta.waktu_selesai = datetime.datetime.now()
#     ujian_peserta.status = "SELESAI"

#     jumlah_soal = Pertanyaan.query.filter(
#         Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
#         Pertanyaan.tipe_pertanyaan == "pilihan_ganda",
#         or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
#     ).count()
#     jawaban_benar = Jawaban.query.join(Pertanyaan).filter(
#         Jawaban.ujian_peserta_id == ujian_peserta.id, Jawaban.benar == True, Pertanyaan.tipe_pertanyaan == "pilihan_ganda"
#     ).count()
#     ujian_peserta.hasil = jawaban_benar / jumlah_soal * 100

#     db.session.commit()

#     flash("Anda telah menyelesaikan ujian.", "success")
#     return redirect(url_for("doing.code"))

## perbaikan kode baru untuk soal pilihan ganda, ceklist, benar salah, sesuai tidak sesuai serta uraian
@bp.route("/end", methods=["GET", "POST"])
@login_required
def end():
    ujian_peserta: UjianPeserta = UjianPeserta.query.filter(
        UjianPeserta.user_id == current_user.id,
        UjianPeserta.status == "BERJALAN",
        or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
    ).first()
    if ujian_peserta is None:
        abort(404)

    ujian_peserta.waktu_selesai = datetime.datetime.now()
    ujian_peserta.status = "SELESAI"

    # 1. Hitung Total Soal (Semua Tipe)
    jumlah_soal = Pertanyaan.query.filter(
        Pertanyaan.pelajaran_id == ujian_peserta.pelajaran_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).count()
    
    # 2. Hitung Jawaban Benar (Semua Tipe)
    # Menggunakan > 0 agar lebih aman daripada == True
    jawaban_benar = Jawaban.query.filter(
        Jawaban.ujian_peserta_id == ujian_peserta.id, 
        Jawaban.benar > 0, 
        or_(Jawaban.deleted.is_(None), Jawaban.deleted != True)
    ).count()

    if jumlah_soal > 0:
        ujian_peserta.hasil = jawaban_benar / jumlah_soal * 100
    else:
        ujian_peserta.hasil = 0

    db.session.commit()

    flash("Anda telah menyelesaikan ujian.", "success")
    return redirect(url_for("doing.code"))
    
# @bp.route("/uraian/<ujian_peserta_id>", methods=["POST"])
# @login_required
# @csrf.exempt
# @role_required(roles=["admin", "proktor"])
# def uraian(ujian_peserta_id):
#     if request.method == "POST":
#         errors = []

#         number = request.form.get("nomor")
#         nilai = request.form.get("nilai")

#         if nilai == "":
#             errors.append("Nilai tidak boleh kosong.")

#         nomor_check: Jawaban = Jawaban.query.filter(
#             Jawaban.nomor == number,
#             or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
#         ).first()
#         if nomor_check is None:
#             flash("Nomor soal tidak ditemukan.", "error")
#             return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

#         pertanyaan: Pertanyaan = Pertanyaan.query.filter(
#             Pertanyaan.id == nomor_check.pertanyaan_id,
#             Pertanyaan.tipe_pertanyaan == "uraian"
#         ).first()
#         if pertanyaan is None:
#             flash("Tipe soal bukan uraian.", "error")
#             return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

#         if len(errors) > 0:
#             flash("\\n".join(errors), "error")
#         else:
#             penilaian: Jawaban = Jawaban.query.filter(
#                 Jawaban.nomor == number,
#                 Jawaban.ujian_peserta_id == ujian_peserta_id,
#                 or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
#             ).first()

#             if penilaian is None:
#                 abort(404)

#             hasil: UjianPeserta = UjianPeserta.query.filter(
#                 UjianPeserta.id == ujian_peserta_id,
#                 or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
#             ).first()

#             if hasil is None:
#                 abort(404)

#             penilaian.benar = nilai

#             db.session.commit()

#             flash("Berhasil menyimpan", "success")
#             return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

#     return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))
@bp.route("/uraian/<ujian_peserta_id>", methods=["POST"])
@login_required
@csrf.exempt
@role_required(roles=["admin", "proktor"])
def uraian(ujian_peserta_id):
    if request.method == "POST":
        errors = []

        number = request.form.get("nomor")
        nilai = request.form.get("nilai")

        if nilai == "":
            errors.append("Nilai tidak boleh kosong.")

        nomor_check: Jawaban = Jawaban.query.filter(
            Jawaban.nomor == number,
            Jawaban.ujian_peserta_id == ujian_peserta_id, # Tambahkan filter ini untuk akurasi
            or_(Jawaban.deleted.is_(None), Jawaban.deleted != True),
        ).first()
        
        if nomor_check is None:
            flash("Jawaban tidak ditemukan.", "error")
            return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

        # Cek tipe soal dari tabel Pertanyaan
        pertanyaan: Pertanyaan = Pertanyaan.query.filter(
            Pertanyaan.id == nomor_check.pertanyaan_id
        ).first()
        
        if pertanyaan is None or pertanyaan.tipe_pertanyaan != "uraian":
            flash("Tipe soal bukan uraian.", "error")
            return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

        if len(errors) > 0:
            flash("\n".join(errors), "error")
        else:
            # 1. Simpan Nilai Uraian
            nomor_check.benar = nilai
            # db.session.commit() # Commit nanti sekalian update hasil

            # 2. Hitung Ulang Total Nilai Siswa
            # Ambil data peserta
            hasil: UjianPeserta = UjianPeserta.query.filter(
                UjianPeserta.id == ujian_peserta_id,
                or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True),
            ).first()

            if hasil:
                # Hitung total soal (Semua tipe)
                jumlah_soal = Pertanyaan.query.filter(
                    Pertanyaan.pelajaran_id == hasil.pelajaran_id,
                    or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
                ).count()
                
                # Hitung jawaban benar (Nilai > 0 dianggap benar/dapat poin)
                # Ini mengasumsikan 1 soal = 1 poin dalam perhitungan count
                # Jika Anda memberi nilai uraian 10, ini tetap dihitung 1 soal benar oleh .count()
                jawaban_benar = Jawaban.query.filter(
                    Jawaban.ujian_peserta_id == hasil.id, 
                    Jawaban.benar > 0, # Ubah logika ke > 0 agar nilai angka masuk
                    or_(Jawaban.deleted.is_(None), Jawaban.deleted != True)
                ).count()

                if jumlah_soal > 0:
                    hasil.hasil = jawaban_benar / jumlah_soal * 100
                else:
                    hasil.hasil = 0
            
            db.session.commit()

            flash("Berhasil menyimpan dan memperbarui nilai.", "success")
            return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))

    return redirect(url_for("exam.review", ujian_peserta_id=ujian_peserta_id))