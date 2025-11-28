import click
from flask.cli import AppGroup

from app import db
from app.models import (
    Config,
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

tool_cli = AppGroup("tool")


@tool_cli.command("clean")
def create_user():
    try:
        print("start cleaning")
        print("cleaning config")
        Config.query.delete()
        print("cleaning gambar")
        Gambar.query.delete()
        print("cleaning jadwal ujian")
        JadwalUjian.query.delete()
        print("cleaning jawaban")
        Jawaban.query.delete()
        print("cleaning kecamatan")
        Kecamatan.query.delete()
        print("cleaning log error")
        LogError.query.delete()
        print("cleaning pelajaran")
        Pelajaran.query.delete()
        print("cleaning pelajaran ujian")
        PelajaranUjian.query.delete()
        print("cleaning pertanyaan")
        Pertanyaan.query.delete()
        print("cleaning rombaongan belajar")
        RombonganBelajar.query.delete()
        print("cleaning sekolah")
        Sekolah.query.delete()
        print("cleaning ujian")
        Ujian.query.delete()
        print("cleaning ujian peserta")
        UjianPeserta.query.delete()
        print("cleaning ujian sekolah")
        UjianSekolah.query.delete()
        print("cleaning user")
        User.query.delete()

        db.session.commit()
        print("finish")
    except Exception as e:
        print(e)
