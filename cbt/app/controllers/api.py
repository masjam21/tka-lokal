from datetime import datetime
import traceback
import logging

from app import csrf, db
from app.decorators import token_required
from app.models import (
    Gambar,
    JadwalUjian,
    Jawaban,
    Kecamatan,
    LogError,
    Pelajaran,
    PelajaranUjian,
    Pertanyaan,
    RombonganBelajar,
    Sekolah,
    Ujian,
    UjianPeserta,
    UjianSekolah,
    User,
)
from flask import Blueprint, jsonify, request
from sqlalchemy import or_

bp = Blueprint("api", __name__)


@bp.route("/get-proktor-data", methods=["POST"])
@csrf.exempt
def get_proktor_data():
    date_format = "%Y/%m/%d %H:%M"
    errors = []

    try:
        body = request.get_json(force=True)
    except:
        errors.append("Json tidak valid.")
        return jsonify({"message": errors[0], "errors": errors}), 400

    username = body["username"] if "username" in body else ""
    password = body["password"] if "password" in body else ""

    if username == "":
        errors.append("Username tidak boleh kosong.")
    if password == "":
        errors.append("Password tidak boleh kosong.")

    if len(errors) == 0:
        user: User = User.query.filter(User.username == username).first()
        if user is None:
            errors.append("Username tidak ditemukan.")
        elif user.role != "proktor":
            errors.append("User bukan proktor.")
        elif not user.check_password(password):
            errors.append("Password salah.")

    if len(errors) > 0:
        return jsonify({"message": errors[0], "errors": errors}), 400

    kecamatan: list[Kecamatan] = Kecamatan.query.all()
    kecamatan_list = []
    for i in kecamatan:
        kecamatan_list.append(
            {
                "id": i.id,
                "nama": i.nama,
                "created_at": datetime.strftime(i.created_at, date_format)
                if i.created_at is not None
                else None,
                "updated_at": datetime.strftime(i.updated_at, date_format)
                if i.updated_at is not None
                else None,
            }
        )
    sekolah: Sekolah = Sekolah.query.get(user.sekolah_id)

    return jsonify(
        {
            "kecamatan": kecamatan_list,
            "sekolah": {
                "id": sekolah.id,
                "nama": sekolah.nama,
                "npsn": sekolah.npsn,
                "kecamatan_id": sekolah.kecamatan_id,
                "alamat": sekolah.alamat,
                "email": sekolah.email,
                "kepala_sekolah": sekolah.kepala_sekolah,
                "no_hp_kepala_sekolah": sekolah.no_hp_kepala_sekolah,
                "nip_kepala_sekolah": sekolah.nip_kepala_sekolah,
                "created_at": datetime.strftime(sekolah.created_at, date_format)
                if sekolah.created_at is not None
                else None,
                "updated_at": datetime.strftime(sekolah.updated_at, date_format)
                if sekolah.updated_at is not None
                else None,
            },
            "user": {
                "id": user.id,
                "username": user.username,
                "password": user.password,
                "nama": user.nama,
                "role": user.role,
                "sekolah_id": user.sekolah_id,
                "created_at": datetime.strftime(user.created_at, date_format)
                if user.created_at is not None
                else None,
                "updated_at": datetime.strftime(user.updated_at, date_format)
                if user.updated_at is not None
                else None,
            },
        }
    )


@bp.route("/get-data", methods=["POST"])
@csrf.exempt
@token_required
def get_data():
    errors = []

    try:
        body = request.get_json(force=True)
    except:
        errors.append("Json tidak valid.")
        return jsonify({"message": errors[0], "errors": errors}), 400

    proktor_id = body["proktor_id"] if "proktor_id" in body else ""
    latest_update_str = body["latest_update"] if "latest_update" in body else ""

    if proktor_id == "":
        errors.append("Proktor tidak boleh kosong.")

    if latest_update_str != None and latest_update_str != "":
        try:
            latest_update = datetime.strptime(latest_update_str, "%Y/%m/%d %H:%M:%S")
        except Exception:
            errors.append("Format tanggal tidak sesuai.")

    if len(errors) == 0:
        proktor: User = User.query.filter(
            User.id == proktor_id,
            or_(User.deleted.is_(None), User.deleted == False),
        ).first()
        if proktor is None:
            errors.append("Proktor tidak ditemukan.")

    if len(errors) > 0:
        return jsonify({"errors": errors, "message": errors[0]}), 400
    else:
        date_format = "%Y/%m/%d %H:%M"

        # update proktor
        proktor: User = User.query.filter(User.id == proktor_id).first()

        # update sekolah
        sekolah: Sekolah = Sekolah.query.filter(
            Sekolah.id == proktor.sekolah_id
        ).first()

        # update rombongan belajar
        rombongan_belajar_list = []
        rombongan_belajar: list[RombonganBelajar] = RombonganBelajar.query.filter(
            RombonganBelajar.sekolah_id == sekolah.id
        ).all()

        for i in rombongan_belajar:
            rombongan_belajar_list.append(
                {
                    "id": i.id,
                    "sekolah_id": i.sekolah_id,
                    "tingkat_pendidikan": i.tingkat_pendidikan,
                    "nama": i.nama,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # update peserta
        peserta: list[User] = User.query.filter(
            User.sekolah_id == sekolah.id, User.role == "peserta_didik"
        ).all()
        peserta_list = []
        for i in peserta:
            peserta_list.append(
                {
                    "id": i.id,
                    "username": i.username,
                    "nama": i.nama,
                    "role": i.role,
                    "password": i.password,
                    "sekolah_id": i.sekolah_id,
                    "nis": i.nis,
                    "nik": i.nik,
                    "ibu": i.ibu,
                    "ayah": i.ayah,
                    "alamat": i.alamat,
                    "jenis_kelamin": i.jenis_kelamin,
                    "rombongan_belajar_id": i.rombongan_belajar_id,
                    "tempat_lahir": i.tempat_lahir,
                    "tanggal_lahir": datetime.strftime(i.tanggal_lahir, date_format)
                    if i.tanggal_lahir is not None
                    else None,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # ambil pelajaran
        pelajaran: list[Pelajaran] = Pelajaran.query.all()
        pelajaran_list = []
        for i in pelajaran:
            pelajaran_list.append(
                {
                    "id": i.id,
                    "kode": i.kode,
                    "nama": i.nama,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # get pertanyaan
        # pertanyaan: list[Pertanyaan] = Pertanyaan.query.all()
        pertanyaan: list[Pertanyaan] = (
            session.query(
                Pertanyaan.id, Pertanyaan.pelajaran_id, Pertanyaan.pertanyaan, Pertanyaan.jumlah_pilihan, 
                Pertanyaan.tipe_pertanyaan, Pertanyaan.pilihan_a, Pertanyaan.pilihan_b, Pertanyaan.pilihan_c, 
                Pertanyaan.pilihan_d, Pertanyaan.jawaban, Pertanyaan.created_at, Pertanyaan.updated_at, Pertanyaan.deleted,
                # TAMBAHKAN SEMUA KOLOM BARU INI
                Pertanyaan.pernyataan_1, Pertanyaan.pernyataan_2, Pertanyaan.pernyataan_3,
                Pertanyaan.jawaban_1, Pertanyaan.jawaban_2, Pertanyaan.jawaban_3
            ).join(Pelajaran, Pelajaran.id == Pertanyaan.pelajaran_id, isouter=True).filter(Pelajaran.is_allowed_to_sync == 1).all()
        )

        pertanyaan_list = []
        for i in pertanyaan:
            pertanyaan_list.append(
                {
                    "id": i.id,
                    "pelajaran_id": i.pelajaran_id,
                    "pertanyaan": i.pertanyaan,
                    "jumlah_pilihan": i.jumlah_pilihan,
                    "tipe_pertanyaan": i.tipe_pertanyaan,
                    "pilihan_a": i.pilihan_a,
                    "pilihan_b": i.pilihan_b,
                    "pilihan_c": i.pilihan_c,
                    "pilihan_d": i.pilihan_d,
                    # "pilihan_e": i.pilihan_e,
                    "jawaban": i.jawaban,
                    "pernyataan_1": i.pernyataan_1,
                    "pernyataan_2": i.pernyataan_2,
                    "pernyataan_3": i.pernyataan_3,
                    "jawaban_1": i.jawaban_1,
                    "jawaban_2": i.jawaban_2,
                    "jawaban_3": i.jawaban_3,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # get gambar
        gambar: list[Gambar] = Gambar.query.all()
        gambar_list = []
        for i in gambar:
            gambar_list.append(
                {
                    "id": i.id,
                    "nama": i.nama,
                    "data_gambar": i.data_gambar,
                    "pelajaran_id": i.pelajaran_id,
                    "deleted": i.deleted,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                }
            )

        # ambil pelajaran ujian
        palajaran_ujian: list[PelajaranUjian] = PelajaranUjian.query.all()
        pelajaran_ujian_list = []
        for i in palajaran_ujian:
            pelajaran_ujian_list.append(
                {
                    "id": i.id,
                    "ujian_id": i.ujian_id,
                    "pelajaran_id": i.pelajaran_id,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # ambil ujian
        ujian: list[Ujian] = Ujian.query.all()
        ujian_list = []
        for i in ujian:
            ujian_list.append(
                {
                    "id": i.id,
                    "nama": i.nama,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        # ambil jadwal
        jadwal: list[JadwalUjian] = JadwalUjian.query.all()
        jadwal_list = []
        for i in jadwal:
            jadwal_list.append(
                {
                    "id": i.id,
                    "ujian_id": i.ujian_id,
                    "pelajaran_id": i.pelajaran_id,
                    "sesi": i.sesi,
                    "tanggal": datetime.strftime(i.tanggal, date_format)
                    if i.tanggal is not None
                    else None,
                    "durasi": i.durasi,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        return jsonify(
            {
                "proktor": {
                    "username": proktor.username,
                    "nama": proktor.nama,
                    "password": proktor.password,
                    "sekolah_id": proktor.sekolah_id,
                    "created_at": datetime.strftime(proktor.created_at, date_format)
                    if proktor.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(proktor.updated_at, date_format)
                    if proktor.updated_at is not None
                    else None,
                    "deleted": proktor.deleted,
                },
                "sekolah": {
                    "nama": sekolah.nama,
                    "npsn": sekolah.npsn,
                    "kecamatan_id": sekolah.kecamatan_id,
                    "alamat": sekolah.alamat,
                    "email": sekolah.email,
                    "kepala_sekolah": sekolah.kepala_sekolah,
                    "no_hp_kepala_sekolah": sekolah.no_hp_kepala_sekolah,
                    "nip_kepala_sekolah": sekolah.nip_kepala_sekolah,
                    "password": sekolah.password,
                    "created_at": datetime.strftime(sekolah.created_at, date_format)
                    if sekolah.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(sekolah.updated_at, date_format)
                    if sekolah.updated_at is not None
                    else None,
                    "deleted": sekolah.deleted,
                }
                if sekolah is not None
                else None,
                "rombongan_belajar": rombongan_belajar_list,
                "peserta_didik": peserta_list,
                "pelajaran": pelajaran_list,
                "pertanyaan": pertanyaan_list,
                "gambar": gambar_list,
                "ujian": ujian_list,
                "pelajaran_ujian": pelajaran_ujian_list,
                "jadwal_ujian": jadwal_list,
            }
        )


@bp.route("/upload-result", methods=["POST"])
@csrf.exempt
@token_required
def upload_result():
    errors = []
    try:
        body = request.get_json(force=True)
    except:
        errors.append("Json tidak valid.")
        return jsonify({"message": errors[0], "errors": errors}), 400

    proktor_id = body["proktor_id"] if "proktor_id" in body else ""
    proktor = User.query.filter(
        User.id == proktor_id,
        User.role == "proktor",
        or_(User.deleted.is_(None), User.deleted != True),
    ).first()
    if proktor is None:
        errors.append("Proktor tidak ditemukan.")
        return jsonify({"message": errors[0], "errors": errors}), 400

    try:
        # update proktor
        proktor_json = body["proktor"]
        proktor: User = User.query.filter(User.id == proktor_id).first()
        proktor.username = proktor_json["username"]
        proktor.nama = proktor_json["nama"]
        proktor.password = proktor_json["password"]
        proktor.sekolah_id = proktor_json["sekolah_id"]
        proktor.created_at = proktor_json["created_at"]
        proktor.updated_at = proktor_json["updated_at"]
        proktor.deleted = proktor_json["deleted"]

        # update sekolah
        sekolah_json = body["sekolah"]
        sekolah: Sekolah = Sekolah.query.filter(
            Sekolah.id == proktor_json["sekolah_id"]
        ).first()
        sekolah.nama = sekolah_json["nama"]
        sekolah.npsn = sekolah_json["npsn"]
        sekolah.kecamatan_id = sekolah_json["kecamatan_id"]
        sekolah.alamat = sekolah_json["alamat"]
        sekolah.email = sekolah_json["email"]
        sekolah.kepala_sekolah = sekolah_json["kepala_sekolah"]
        sekolah.no_hp_kepala_sekolah = sekolah_json["no_hp_kepala_sekolah"]
        sekolah.nip_kepala_sekolah = sekolah_json["nip_kepala_sekolah"]
        sekolah.password = sekolah_json["password"]
        sekolah.created_at = sekolah_json["created_at"]
        sekolah.updated_at = sekolah_json["updated_at"]
        sekolah.deleted = sekolah_json["deleted"]
        sekolah.latest_upload = sekolah_json["latest_upload"]

        # update rombongan belajar
        rombongan_belajar_json = body["rombongan_belajar"]
        for i in rombongan_belajar_json:
            rombel = RombonganBelajar()
            rombel.id = i["id"]
            rombel.sekolah_id = i["sekolah_id"]
            rombel.tingkat_pendidikan = i["tingkat_pendidikan"]
            rombel.nama = i["nama"]
            rombel.created_at = i["created_at"]
            rombel.updated_at = i["updated_at"]
            rombel.deleted = i["deleted"]
            db.session.merge(rombel)

        # peserta didik
        for i in body["peserta_didik"]:
            user = User()
            user.id = i["id"]
            user.username = i["username"]
            user.nama = i["nama"]
            user.role = i["role"]
            user.password = i["password"]
            user.sekolah_id = i["sekolah_id"]
            user.nis = i["nis"]
            user.nik = i["nik"]
            user.ibu = i["ibu"]
            user.ayah = i["ayah"]
            user.alamat = i["alamat"]
            user.jenis_kelamin = i["jenis_kelamin"]
            user.rombongan_belajar_id = i["rombongan_belajar_id"]
            user.tempat_lahir = i["tempat_lahir"]
            user.tanggal_lahir = i["tanggal_lahir"]
            user.created_at = i["created_at"]
            user.updated_at = i["updated_at"]
            user.deleted = i["deleted"]
            db.session.merge(user)

        for i in body["ujian_sekolah"]:
            ujian_sekolah = UjianSekolah()
            ujian_sekolah.id = i["id"]
            ujian_sekolah.ujian_id = i["ujian_id"]
            ujian_sekolah.pelajaran_id = i["pelajaran_id"]
            ujian_sekolah.jadwal_ujian_id = i["jadwal_ujian_id"]
            ujian_sekolah.sekolah_id = i["sekolah_id"]

            ujian_sekolah.status = i["status"]
            ujian_sekolah.kode = i["kode"]

            ujian_sekolah.created_at = i["created_at"]
            ujian_sekolah.updated_at = i["updated_at"]

            ujian_sekolah.deleted = i["deleted"]
            db.session.merge(ujian_sekolah)

        for i in body["ujian_peserta"]:
            ujian_peserta = UjianPeserta()
            ujian_peserta.id = i["id"]
            ujian_peserta.user_id = i["user_id"]
            ujian_peserta.ujian_id = i["ujian_id"]
            ujian_peserta.pelajaran_id = i["pelajaran_id"]
            ujian_peserta.jadwal_ujian_id = i["jadwal_ujian_id"]
            ujian_peserta.sekolah_id = i["sekolah_id"]

            # status = BARU, BERJALAN, SELESAI
            ujian_peserta.status = i["status"]
            ujian_peserta.hasil = i["hasil"]
            ujian_peserta.waktu_mulai = i["waktu_mulai"]
            ujian_peserta.waktu_selesai = i["waktu_selesai"]

            ujian_peserta.created_at = i["created_at"]
            ujian_peserta.updated_at = i["updated_at"]

            ujian_peserta.deleted = i["deleted"]
            db.session.merge(ujian_peserta)

        for i in body["jawaban"]:
            jawaban = Jawaban()
            jawaban.id = i["id"]
            jawaban.user_id = i["user_id"]
            jawaban.ujian_id = i["ujian_id"]
            jawaban.pelajaran_id = i["pelajaran_id"]
            jawaban.jadwal_ujian_id = i["jadwal_ujian_id"]
            jawaban.sekolah_id = i["sekolah_id"]
            jawaban.ujian_peserta_id = i["ujian_peserta_id"]
            jawaban.pertanyaan_id = i["pertanyaan_id"]

            jawaban.jawaban = i["jawaban"]
            jawaban.benar = i["benar"]
            jawaban.nomor = i["nomor"]

            jawaban.created_at = i["created_at"]
            jawaban.updated_at = i["updated_at"]

            jawaban.deleted = i["deleted"]
            db.session.merge(jawaban)

        db.session.commit()

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"message": "terjadi kesalahan"}), 400

    return jsonify({"message": "success"})


@bp.route("/log-error", methods=["POST"])
@csrf.exempt
@token_required
def log_error():
    body = request.get_json(force=True)
    proktor_id = body["proktor_id"] if "proktor_id" in body else ""
    message = body["message"] if "message" in body else ""
    traceback_message = body["traceback"] if "traceback" in body else ""

    errors = []
    if (
        proktor_id == ""
        and User.query.filter(
            User.id == proktor_id, or_(User.deleted.is_(None), User.deleted != True)
        ).first()
        is None
    ):
        errors.append("Proktor id tidak ditemukan.")

    if len(errors) > 0:
        return jsonify({"message": errors[0], "errors": errors}), 400

    log_error = LogError()
    if proktor_id != "":
        log_error.user_id = proktor_id
    log_error.message = message
    log_error.traceback = traceback_message

    db.session.add(log_error)
    db.session.commit()

    return jsonify({"message": "success"})
