import logging
import os
import traceback
from datetime import datetime

import requests
from app import csrf, db
from app.decorators import role_required
from app.models import (
    Gambar,
    JadwalUjian,
    Jawaban,
    Kecamatan,
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
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    Response
)
from flask_login import current_user, login_required, login_user
from sqlalchemy import or_, create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy

import io
import csv
import pysftp
import subprocess

bp = Blueprint("sync", __name__)

@bp.route("/", methods=["GET"])
@bp.route("/list", methods=["GET"])
@login_required
@role_required(roles=["proktor"])
def show():
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/tka')
    Session = sessionmaker(bind = engine)
    session = Session()
    exam_list: list(Ujian) = (
        Ujian.query.filter(or_(Ujian.deleted.is_(None), Ujian.deleted != True))
        .order_by(Ujian.nama.asc())
        .all()
    )
    # exam_list: list(Ujian) = (
    #     session.query(Ujian.id, Ujian.nama).join(UjianSekolah, Ujian.id == UjianSekolah.ujian_id, isouter=False).filter(UjianSekolah.status == "SELESAI", or_(Ujian.deleted.is_(None), UjianSekolah.deleted != True)).all()
    # )

    return render_template(
        "sync/sync.html",
        title="Sinkronisasi",
        exam_list=exam_list,
    )

@bp.route("/sync", methods=["GET", "POST"])
#@csrf.exempt
@login_required
def sync():
    server_url = os.environ.get("SERVER_CENTRAL_URL")
    try:
        # modified by grey
        date_format = "%Y/%m/%d %H:%M"
        peserta: list[User] = User.query.filter(
            User.sekolah_id == Sekolah.id, or_(User.role == "peserta_didik", User.role == "proktor")
        ).all()

        if peserta is not None:
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

        proktor: User = User.query.filter(User.id == current_user.id).first()

        # end modify by grey

        if peserta is not None:
            r = requests.post(
                server_url + "/api/get-data",
                json={
                    "proktor_id": current_user.id,
                    "peserta_didik": peserta_list,
                    "latest_update": datetime.strftime(
                        current_user.latest_update, "%Y/%m/%d %H:%M:%S"
                    )
                    if current_user.latest_update is not None
                    else None,
                },
                headers={"token": os.environ.get("API_KEY")},
                verify=False,
            )
        else:
            r = requests.post(
                server_url + "/api/get-data",
                json={
                    "proktor_id": current_user.id,
                    "latest_update": datetime.strftime(
                        current_user.latest_update, "%Y/%m/%d %H:%M:%S"
                    )
                    if current_user.latest_update is not None
                    else None,
                },
                headers={"token": os.environ.get("API_KEY")},
                verify=False,
            )


        if r is None:
            flash("Terjadi kesalahan koneksi internet ke server", "error")
        else:
            if r.status_code == 400:
                json_response = r.json()
                flash("\\n".join(json_response["errors"]), "error")

            elif r.status_code == 403:
                flash("Akses tidak diperbolehkan.", "error")

            elif r.status_code == 200:
                json_response = r.json()

                # update proktor
                proktor_json = json_response["proktor"]
                proktor: User = User.query.filter(User.id == current_user.id).first()
                proktor.username = proktor_json["username"]
                proktor.nama = proktor_json["nama"]
                proktor.password = proktor_json["password"]
                proktor.sekolah_id = proktor_json["sekolah_id"]
                proktor.created_at = proktor_json["created_at"]
                proktor.updated_at = proktor_json["updated_at"]
                proktor.deleted = proktor_json["deleted"]

                # update sekolah
                sekolah_json = json_response["sekolah"]
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

                # update rombongan belajar
                rombongan_belajar_json = json_response["rombongan_belajar"]
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
                for i in json_response["peserta_didik"]:
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

                # pelajaran
                for i in json_response["pelajaran"]:
                    palajaran = Pelajaran()
                    palajaran.id = i["id"]
                    palajaran.kode = i["kode"]
                    palajaran.nama = i["nama"]
                    palajaran.created_at = i["created_at"]
                    palajaran.updated_at = i["updated_at"]
                    palajaran.deleted = i["deleted"]
                    db.session.merge(palajaran)

                # pertanyaan
                for i in json_response["pertanyaan"]:
                    pertanyaan: Pertanyaan = Pertanyaan()
                    pertanyaan.id = i["id"]
                    pertanyaan.pelajaran_id = i["pelajaran_id"]
                    pertanyaan.pertanyaan = i["pertanyaan"]
                    pertanyaan.jumlah_pilihan = i["jumlah_pilihan"]
                    pertanyaan.tipe_pertanyaan = i["tipe_pertanyaan"]
                    pertanyaan.pilihan_a = i["pilihan_a"]
                    pertanyaan.pilihan_b = i["pilihan_b"]
                    pertanyaan.pilihan_c = i["pilihan_c"]
                    pertanyaan.pilihan_d = i["pilihan_d"]
                    # pertanyaan.pilihan_e = i["pilihan_e"]
                    pertanyaan.jawaban = i["jawaban"]

                    pertanyaan.pernyataan_1 = i.get("pernyataan_1")
                    pertanyaan.pernyataan_2 = i.get("pernyataan_2")
                    pertanyaan.pernyataan_3 = i.get("pernyataan_3")
                    pertanyaan.jawaban_1 = i.get("jawaban_1")
                    pertanyaan.jawaban_2 = i.get("jawaban_2")
                    pertanyaan.jawaban_3 = i.get("jawaban_3")

                    pertanyaan.created_at = i["created_at"]
                    pertanyaan.updated_at = i["updated_at"]
                    pertanyaan.deleted = i["deleted"]
                    db.session.merge(pertanyaan)

                # gambar
                for i in json_response["gambar"]:
                    gambar: Gambar = Gambar()
                    gambar.id = i["id"]
                    gambar.nama = i["nama"]
                    gambar.data_gambar = i["data_gambar"]
                    gambar.pelajaran_id = i["pelajaran_id"]
                    gambar.created_at = i["created_at"]
                    gambar.updated_at = i["updated_at"]
                    gambar.deleted = i["deleted"]
                    db.session.merge(gambar)

                # ujian
                for i in json_response["ujian"]:
                    ujian = Ujian()
                    ujian.id = i["id"]
                    ujian.nama = i["nama"]
                    ujian.created_at = i["created_at"]
                    ujian.updated_at = i["updated_at"]
                    ujian.deleted = i["deleted"]
                    db.session.merge(ujian)

                # pelajaran ujian
                for i in json_response["pelajaran_ujian"]:
                    pelajaran_ujian = PelajaranUjian()
                    pelajaran_ujian.id = i["id"]
                    pelajaran_ujian.ujian_id = i["ujian_id"]
                    pelajaran_ujian.pelajaran_id = i["pelajaran_id"]
                    pelajaran_ujian.created_at = i["created_at"]
                    pelajaran_ujian.updated_at = i["updated_at"]
                    pelajaran_ujian.deleted = i["deleted"]
                    db.session.merge(pelajaran_ujian)

                # jadwal ujian
                for i in json_response["jadwal_ujian"]:
                    jadwal_ujian = JadwalUjian()
                    jadwal_ujian.id = i["id"]
                    jadwal_ujian.ujian_id = i["ujian_id"]
                    jadwal_ujian.pelajaran_id = i["pelajaran_id"]
                    jadwal_ujian.sesi = i["sesi"]
                    jadwal_ujian.tanggal = i["tanggal"]
                    jadwal_ujian.durasi = i["durasi"]
                    jadwal_ujian.created_at = i["created_at"]
                    jadwal_ujian.updated_at = i["updated_at"]
                    jadwal_ujian.deleted = i["deleted"]
                    db.session.merge(jadwal_ujian)

                ujian_sekolah_json = json_response["ujian_sekolah"]
                for i in ujian_sekolah_json:
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

                ujian_peserta_json = json_response["ujian_peserta"]
                for i in ujian_peserta_json:
                    ujian_peserta = UjianPeserta()
                    ujian_peserta.id = i["id"]
                    ujian_peserta.user_id = i["user_id"]
                    ujian_peserta.ujian_id = i["ujian_id"]
                    ujian_peserta.pelajaran_id = i["pelajaran_id"]
                    ujian_peserta.jadwal_ujian_id = i["jadwal_ujian_id"]
                    ujian_peserta.sekolah_id = i["sekolah_id"]
                    ujian_peserta.status = i["status"]
                    ujian_peserta.hasil = i["hasil"]
                    ujian_peserta.waktu_mulai = i["waktu_mulai"]
                    ujian_peserta.waktu_selesai = i["waktu_selesai"]
                    ujian_peserta.created_at = i["created_at"]
                    ujian_peserta.updated_at = i["updated_at"]
                    ujian_peserta.deleted = i["deleted"]
                    db.session.merge(ujian_peserta)

                # jawaban_json = json_response["jawaban"]
                # for i in jawaban_json:
                #     jawaban = Jawaban()
                #     jawaban.id = i["id"]
                #     jawaban.user_id = i["user_id"]
                #     jawaban.ujian_id = i["ujian_id"]
                #     jawaban.pelajaran_id = i["pelajaran_id"]
                #     jawaban.jadwal_ujian_id = i["jadwal_ujian_id"]
                #     jawaban.sekolah_id = i["sekolah_id"]
                #     jawaban.ujian_peserta_id = i["ujian_peserta_id"]
                #     jawaban.pertanyaan_id = i["pertanyaan_id"]
                #     jawaban.jawaban = i["jawaban"]
                #     jawaban.benar = i["benar"]
                #     jawaban.nomor = i["nomor"]
                #     jawaban.created_at = i["created_at"]
                #     jawaban.updated_at = i["updated_at"]
                #     jawaban.deleted = i["deleted"]
                #     db.session.merge(jawaban)

                proktor.latest_update = datetime.now()
                sekolah.latest_sync = datetime.now()
                db.session.commit()

                flash("Sukses sinkronisasi data", "success")

            else:
                flash("Terjadi kesalahan.", "error")

    except Exception as e:
        logging.error(traceback.format_exc())
        r = requests.post(
            server_url + "/api/log-error",
            json={
                "proktor_id": current_user.id,
                "message": "sync",
                "traceback": traceback.format_exc(),
            },
            headers={"token": os.environ.get("API_KEY")},
            verify=False,
        )
        flash("Terjadi kesalahan sistem", "error")

    return redirect(url_for("sync.show"))


@bp.route("/proktor", methods=["GET", "POST"])
def get_proktor():
    if User.query.filter(or_(User.deleted.is_(None), User.deleted != True)).count() > 0:
        return redirect(url_for("auth.login"))

    form = {
        "username": "",
        "password": "",
    }

    errors = []

    if request.method == "POST":
        form = request.form
        username = request.form.get("username", default="", type=str)
        password = request.form.get("password", default="", type=str)

        if username == "":
            errors.append("Username tidak boleh kosong.")
        if password == "":
            errors.append("Password tidak boleh kosong.")

        server_url = current_app.config.get("SERVER_CENTRAL_URL")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            try:
                r = requests.post(
                    server_url + "/api/get-proktor-data",
                    json={"username": username, "password": password},
                    verify=False,
                )
                if r is None:
                    flash("Terjadi kesalahan koneksi ke server.", "error")
                else:
                    if r.status_code == 400:
                        json_response = r.json()
                        flash("\\n".join(json_response["errors"]), "error")
                    elif r.status_code == 200:
                        json_response = r.json()

                        # insert kecamatan
                        for i in json_response["kecamatan"]:
                            kecamatan: Kecamatan = Kecamatan(
                                id=i["id"],
                                nama=i["nama"],
                                created_at=i["created_at"],
                                updated_at=i["updated_at"],
                            )
                            db.session.merge(kecamatan)

                        db.session.flush()

                        # insert sekolah
                        sekolah: Sekolah = Sekolah(
                            id=json_response["sekolah"]["id"],
                            nama=json_response["sekolah"]["nama"],
                            npsn=json_response["sekolah"]["npsn"],
                            kecamatan_id=json_response["sekolah"]["kecamatan_id"],
                            alamat=json_response["sekolah"]["alamat"],
                            email=json_response["sekolah"]["email"],
                            kepala_sekolah=json_response["sekolah"]["kepala_sekolah"],
                            no_hp_kepala_sekolah=json_response["sekolah"][
                                "no_hp_kepala_sekolah"
                            ],
                            nip_kepala_sekolah=json_response["sekolah"][
                                "nip_kepala_sekolah"
                            ],
                            created_at=json_response["sekolah"]["created_at"],
                            updated_at=json_response["sekolah"]["updated_at"],
                        )
                        db.session.merge(sekolah)
                        db.session.flush()

                        # insert user
                        user: User = User(
                            id=json_response["user"]["id"],
                            username=json_response["user"]["username"],
                            password=json_response["user"]["password"],
                            nama=json_response["user"]["nama"],
                            role=json_response["user"]["role"],
                            sekolah_id=json_response["user"]["sekolah_id"],
                            created_at=json_response["user"]["created_at"],
                            updated_at=json_response["user"]["updated_at"],
                        )
                        user.latest_update = datetime.now()
                        db.session.merge(user)
                        db.session.commit()

                        login_user(user)
                        flash("Selamat datang.", "success")

                        return redirect(url_for("index"))
                    else:
                        flash("Terjadi Kesalahan.", "error")
                        return redirect(url_for("index"))

            except Exception as e:
                logging.error(traceback.format_exc())
                r = requests.post(
                    server_url + "/api/log-error",
                    json={
                        "proktor_id": "",
                        "message": "sync proktor",
                        "traceback": traceback.format_exc(),
                    },
                    headers={"token": os.environ.get("API_KEY")},
                    verify=False,
                )
                flash("Terjadi kesalahan koneksi internet ke server", "error")

    return render_template("sync/proktor.html", form=form)


@bp.route("/upload", methods=["GET", "POST"])
@csrf.exempt
@login_required
def upload():
    date_format = "%Y/%m/%d %H:%M"
    server_url = os.environ.get("SERVER_CENTRAL_URL")

    # added by grey
    form = {}

    try:
        data = {}

        # added by grey
        form = request.form

        exam_id = request.form.get("exam_id", default="", type=str)

        #added by grey
        
        ujian: Ujian = Ujian.query.filter(
            Ujian.id == exam_id
        ).first()

        data["ujian"] = {
            "id": ujian.id,
            "sekolah_id": current_user.sekolah_id,
        }

        proktor: User = User.query.filter(User.id == current_user.id).first()
        data["proktor"] = {
            "id": proktor.id,
            "username": proktor.username,
            "nama": proktor.nama,
            "role": proktor.role,
            "password": proktor.password,
            "sekolah_id": proktor.sekolah_id,
            "created_at": datetime.strftime(proktor.created_at, date_format)
            if proktor.created_at is not None
            else None,
            "updated_at": datetime.strftime(proktor.updated_at, date_format)
            if proktor.updated_at is not None
            else None,
            "deleted": proktor.deleted,
            "latest_update": datetime.strftime(proktor.latest_update, date_format)
            if proktor.latest_update is not None
            else None,
            "latest_upload": datetime.strftime(proktor.latest_upload, date_format)
            if proktor.latest_upload is not None
            else None,
        }

        sekolah: Sekolah = Sekolah.query.filter(
            Sekolah.id == proktor.sekolah_id
        ).first()
        # data["sekolah"] = {
        #     "id": sekolah.id,
        #     "nama": sekolah.nama,
        #     "npsn": sekolah.npsn,
        #     "kecamatan_id": sekolah.kecamatan_id,
        #     "alamat": sekolah.alamat,
        #     "email": sekolah.email,
        #     "kepala_sekolah": sekolah.kepala_sekolah,
        #     "no_hp_kepala_sekolah": sekolah.no_hp_kepala_sekolah,
        #     "nip_kepala_sekolah": sekolah.nip_kepala_sekolah,
        #     "password": sekolah.password,
        #     "deleted": sekolah.deleted,
        #     "created_at": datetime.strftime(proktor.created_at, date_format)
        #     if proktor.created_at is not None
        #     else None,
        #     "updated_at": datetime.strftime(proktor.updated_at, date_format)
        #     if proktor.updated_at is not None
        #     else None,
        # }

        # rombel: list[RombonganBelajar] = RombonganBelajar.query.filter(
        #     RombonganBelajar.sekolah_id == sekolah.id
        # ).all()
        # rombel_list = []
        # for i in rombel:
        #     rombel_list.append(
        #         {
        #             "id": i.id,
        #             "sekolah_id": i.sekolah_id,
        #             "tingkat_pendidikan": i.tingkat_pendidikan,
        #             "nama": i.nama,
        #             "deleted": i.deleted,
        #             "created_at": datetime.strftime(proktor.created_at, date_format)
        #             if proktor.created_at is not None
        #             else None,
        #             "updated_at": datetime.strftime(proktor.updated_at, date_format)
        #             if proktor.updated_at is not None
        #             else None,
        #         }
        #     )

        # data["rombongan_belajar"] = rombel_list

        peserta: list[User] = User.query.filter(User.sekolah_id == sekolah.id).all()
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
                    "deleted": i.deleted,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                }
            )

        data["peserta_didik"] = peserta_list

        engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@127.0.0.1:3306/tka')
        Session = sessionmaker(bind = engine)
        session = Session()

        # ujian sekolah
        # ujian_sekolah: list[UjianSekolah] = UjianSekolah.query.all()
        ujian_sekolah: list[UjianSekolah] = (
            session.query(UjianSekolah.id, UjianSekolah.ujian_id, UjianSekolah.pelajaran_id, UjianSekolah.jadwal_ujian_id, UjianSekolah.sekolah_id, UjianSekolah.status, UjianSekolah.kode, UjianSekolah.deleted, UjianSekolah.created_at, UjianSekolah.updated_at).join(Ujian, Ujian.id == UjianSekolah.ujian_id, isouter=True).filter(UjianSekolah.ujian_id == exam_id, or_(UjianSekolah.deleted.is_(None), UjianSekolah.deleted != True)).all()
        )
        ujian_sekolah_list = []
        for i in ujian_sekolah:
            ujian_sekolah_list.append(
                {
                    "id": i.id,
                    "ujian_id": i.ujian_id,
                    "pelajaran_id": i.pelajaran_id,
                    "jadwal_ujian_id": i.jadwal_ujian_id,
                    "sekolah_id": i.sekolah_id,
                    "status": i.status,
                    "kode": i.kode,
                    "deleted": i.deleted,
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                }
            )
        data["ujian_sekolah"] = ujian_sekolah_list

        # ujian peserta
        # ujian_peserta: list[UjianPeserta] = UjianPeserta.query.all()
        ujian_peserta: list[UjianPeserta] = (
            session.query(UjianPeserta.id, UjianPeserta.user_id, UjianPeserta.ujian_id, UjianPeserta.pelajaran_id, UjianPeserta.jadwal_ujian_id, UjianPeserta.sekolah_id, UjianPeserta.status, UjianPeserta.hasil, UjianPeserta.waktu_mulai, UjianPeserta.waktu_selesai, UjianPeserta.created_at, UjianPeserta.updated_at, UjianPeserta.deleted).join(Ujian, Ujian.id == UjianPeserta.ujian_id, isouter=True).filter(UjianPeserta.ujian_id == exam_id, or_(UjianPeserta.deleted.is_(None), UjianPeserta.deleted != True)).all()
        )
        ujian_peserta_list = []
        for i in ujian_peserta:
            ujian_peserta_list.append(
                {
                    "id": i.id,
                    "user_id": i.user_id,
                    "ujian_id": i.ujian_id,
                    "pelajaran_id": i.pelajaran_id,
                    "jadwal_ujian_id": i.jadwal_ujian_id,
                    "sekolah_id": i.sekolah_id,
                    "status": i.status,
                    "hasil": i.hasil,
                    "waktu_mulai": datetime.strftime(i.waktu_mulai, date_format)
                    if i.waktu_mulai is not None
                    else None,
                    "waktu_selesai": datetime.strftime(i.waktu_selesai, date_format)
                    if i.waktu_selesai is not None
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
        data["ujian_peserta"] = ujian_peserta_list

        # jawaban
        # jawaban: list[Jawaban] = Jawaban.query.all()
        jawaban: list[Jawaban] = (
            session.query(Jawaban.id, Jawaban.user_id, Jawaban.ujian_id, Jawaban.pelajaran_id, Jawaban.jadwal_ujian_id, Jawaban.sekolah_id, Jawaban.ujian_peserta_id, Jawaban.pertanyaan_id, Jawaban.jawaban, Jawaban.benar, Jawaban.nomor, Jawaban.created_at, Jawaban.updated_at, Jawaban.deleted).join(Ujian, Ujian.id == Jawaban.ujian_id, isouter=True).filter(Jawaban.ujian_id == exam_id, or_(Jawaban.deleted.is_(None), Jawaban.deleted != True)).all()
        )
        jawaban_list = []
        for i in jawaban:
            jawaban_list.append(
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
                    "created_at": datetime.strftime(i.created_at, date_format)
                    if i.created_at is not None
                    else None,
                    "updated_at": datetime.strftime(i.updated_at, date_format)
                    if i.updated_at is not None
                    else None,
                    "deleted": i.deleted,
                }
            )

        data["jawaban"] = jawaban_list

        r = requests.post(
            server_url + "/api/upload-result",
            json={"proktor_id": current_user.id, **data},
            headers={"token": os.environ.get("API_KEY")},
            verify=False,
        )
        if r is None:
            flash("Terjadi kesalahan koneksi internet ke server", "error")
        else:
            if r.status_code == 400:
                json_response = r.json()
                flash("\\n".join(json_response["errors"]), "error")

            elif r.status_code == 403:
                flash("Akses tidak diperbolehkan.", "error")

            elif r.status_code == 200:
                flash("Berhasil mengunggah data.", "success")
                proktor.latest_upload = datetime.now()
                db.session.commit()

            else:
                flash("Terjadi kesalahan", "error")

    except Exception as e:
        logging.error(traceback.format_exc())
        r = requests.post(
            server_url + "/api/log-error",
            json={
                "proktor_id": current_user.id,
                "message": "upload",
                "traceback": traceback.format_exc(),
            },
            headers={"token": os.environ.get("API_KEY")},
            verify=False,
        )
        flash("Terjadi kesalahan koneksi internet ke server", "error")

    return redirect(url_for("sync.show"))

@bp.route("/uploadimmediately", methods=["GET", "POST"])
@csrf.exempt
@login_required
def uploadimmediately():
    engine = sqlalchemy.create_engine('mysql://cbt_aspd:Passw0rd123Aspd36!@localhost:3306/cbt')
    Session = sessionmaker(bind = engine)
    session = Session()
    form = {}
    exam_list: list(Ujian) = (
        Ujian.query.filter(or_(Ujian.deleted.is_(None), Ujian.deleted != True))
        .order_by(Ujian.nama.asc())
        .all()
    )
    errors = []
    if request.method == "POST":
        date_format = "%Y/%m/%d %H:%M"
        tanggal_ujian_format = "%Y/%m/%d"

        data = {}
        
        form = request.form

        exam_id = request.form.get("exam_id", default="", type=str)

        if exam_id == "":
            errors.append("Pilih ujian dulu!")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            hasil_ujian: list(UjianPeserta) = (
                session.query(UjianPeserta.id.label("ujian_peserta_id"), Sekolah.nama.label("sekolah"), Sekolah.npsn.label("npsn"), Kecamatan.nama.label("kecamatan"), User.username.label("nisn"), User.nama.label("siswa"), User.nis.label("nis"), User.jenis_kelamin.label("jenis_kelamin"), Ujian.nama.label("ujian"), Pelajaran.kode.label("kode_pelajaran"), Pelajaran.nama.label("mata_pelajaran"), JadwalUjian.tanggal.label("tanggal_ujian"), JadwalUjian.sesi.label("sesi"), JadwalUjian.durasi.label("durasi"), UjianPeserta.status.label("status_ujian"), UjianPeserta.hasil.label("nilai"), UjianPeserta.waktu_mulai.label("waktu_mulai"), UjianPeserta.waktu_selesai.label("waktu_selesai")).join(User, UjianPeserta.user_id == User.id, isouter=False).join(Ujian, UjianPeserta.ujian_id == Ujian.id, isouter=False).join(Pelajaran, UjianPeserta.pelajaran_id == Pelajaran.id, isouter=False).join(JadwalUjian, UjianPeserta.jadwal_ujian_id == JadwalUjian.id, isouter=False).join(Sekolah, UjianPeserta.sekolah_id == Sekolah.id, isouter=False).join(Kecamatan, Sekolah.kecamatan_id == Kecamatan.id).filter(User.role == "peserta_didik", Ujian.id == exam_id).all()
            )

            hasil_ujian_list = []
            for i in hasil_ujian:
                hasil_ujian_list.append(
                    {
                        "ujian_peserta_id": i.ujian_peserta_id,
                        "sekolah": i.sekolah,
                        "npsn": i.npsn,
                        "kecamatan": i.kecamatan,
                        "nisn": i.nisn,
                        "siswa": i.siswa,
                        "nis": i.nis,
                        "jenis_kelamin": i.jenis_kelamin,
                        "ujian": i.ujian,
                        "kode_pelajaran": i.kode_pelajaran,
                        "mata_pelajaran": i.mata_pelajaran,
                        "tanggal_ujian": datetime.strftime(i.tanggal_ujian, tanggal_ujian_format)
                        if i.tanggal_ujian is not None
                        else None,
                        "sesi": i.sesi,
                        "durasi": i.durasi,
                        "status_ujian": i.status_ujian,
                        "nilai": i.nilai,
                        "waktu_mulai": datetime.strftime(i.waktu_mulai, date_format)
                        if i.waktu_mulai is not None
                        else None,
                        "waktu_selesai": datetime.strftime(i.waktu_selesai, date_format)
                        if i.waktu_selesai is not None
                        else None,
                    }
                )

            data["hasil_ujian"] = hasil_ujian_list

            server_url = os.environ.get("SERVER_CENTRAL_URL")

            r = requests.post(
                    server_url + "/api/uploadimmediately",
                    json={"proktor_id": current_user.id, **data},
                    headers={"token": os.environ.get("API_KEY")},
                    verify=False,
                )
            if r is None:
                flash("Terjadi kesalahan koneksi internet ke server", "error")
            else:
                if r.status_code == 400:
                    json_response = r.json()
                    flash("\\n".join(json_response["errors"]), "error")
                elif r.status_code == 403:
                    flash("Akses tidak diperbolehkan.", "error")
                elif r.status_code == 200:
                    flash("Berhasil mengunggah data.", "success")
                else:
                    flash("Terjadi kesalahan", "error")

    return render_template("sync/uploadimmediately.html", title="Unggah Hasil Ujian", form=form, exam_list=exam_list)


## kode untuk shutdown sistem

# @bp.route("/shutdown", methods=["GET"])
# @login_required
# @role_required(roles=["admin", "proktor"]) # Batasi akses
# def shutdown_system():
#     try:
#         # Menjalankan perintah shutdown sistem
#         # -h now : halt (matikan) sekarang
#         flash("Sistem sedang dimatikan...", "success")
        
#         # Menggunakan os.system untuk eksekusi perintah shell
#         # Pastikan user aplikasi punya hak akses sudo tanpa password untuk command ini
#         os.system("sudo /usr/sbin/shutdown -h now")
        
#         return "Sistem sedang dimatikan. Silakan tunggu beberapa saat sebelum mencabut daya."
        
#     except Exception as e:
#         logging.error(traceback.format_exc())
#         flash(f"Gagal mematikan sistem: {str(e)}", "error")
#         return redirect(url_for("sync.show"))