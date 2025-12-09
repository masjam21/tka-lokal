import uuid
from email.policy import default

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    SmallInteger
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(id):
    return User.query.get(id)


class User(db.Model, UserMixin):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    username = Column(String(255))
    nama = Column(String(255))
    # role = admin, operator, pembuat_soal, peserta, kepala_sekolah
    role = Column(String(20))
    password = Column(String(128))
    sekolah_id = Column(String(36), ForeignKey("sekolah.id", ondelete="CASCADE"))
    session_token = db.Column(db.String(255), nullable=True)

    # data peserta
    nis = Column(String(100))
    nik = Column(String(100))
    ibu = Column(String(255))
    ayah = Column(String(255))
    alamat = Column(String(255))
    jenis_kelamin = Column(String(1))
    rombongan_belajar_id = Column(
        String(36), ForeignKey("rombongan_belajar.id", ondelete="CASCADE")
    )
    tempat_lahir = Column(String(255))
    tanggal_lahir = Column(DateTime(timezone=True))

    # data kepala sekolah
    no_hp = Column(String(20))
    nip = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    latest_update = Column(DateTime(timezone=True))
    latest_upload = Column(DateTime(timezone=True))

    ujian_peserta = relationship("UjianPeserta", backref="user", cascade="all, delete")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Config(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    latest_update = Column(DateTime(timezone=True))


class Sekolah(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    nama = Column(String(255))
    npsn = Column(String(100))
    kecamatan_id = db.Column(String(10), ForeignKey("kecamatan.id", ondelete="CASCADE"))
    alamat = Column(String(255))
    email = Column(String(255))
    kepala_sekolah = Column(String(100))
    no_hp_kepala_sekolah = Column(String(20))
    nip_kepala_sekolah = Column(String(50))
    password = Column(String(128))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    latest_sync = Column(DateTime(timezone=True))
    latest_upload = Column(DateTime(timezone=True))

    deleted = Column(Boolean, default=False)

    user = relationship("User", backref="sekolah", cascade="all, delete")
    rombongan_belajar = relationship(
        "RombonganBelajar", backref="sekolah", cascade="all, delete"
    )

    def __str__(self):
        return self.nama

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class RombonganBelajar(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    sekolah_id = Column(String(36), ForeignKey("sekolah.id", ondelete="CASCADE"))
    tingkat_pendidikan = Column(String(2))
    nama = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    user = relationship("User", backref="rombongan_belajar", cascade="all, delete")


class Kecamatan(db.Model):
    id = db.Column(String(10), primary_key=True)
    nama = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    sekolah = relationship("Sekolah", backref="kecamatan", cascade="all, delete")

    def __str__(self):
        return self.nama


class Pelajaran(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    kode = Column(String(255))
    nama = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    pertanyaan = relationship("Pertanyaan", backref="pelajaran", cascade="all, delete")
    pelajaran_ujian = relationship(
        "PelajaranUjian", backref="pelajaran", cascade="all, delete"
    )
    jadwal_ujian = relationship(
        "JadwalUjian", backref="pelajaran", cascade="all, delete"
    )


class Pertanyaan(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    pertanyaan = Column(Text)
    jumlah_pilihan = Column(Integer)
    tipe_pertanyaan = Column(String(50), nullable=True)
    pilihan_a = Column(Text, nullable=True)
    pilihan_b = Column(Text, nullable=True)
    pilihan_c = Column(Text, nullable=True)
    pilihan_d = Column(Text, nullable=True)
    # pilihan_e = Column(Text, nullable=True)
    jawaban = Column(String(20), nullable=True)

    # mode by masjam (untuk soal jenis tertentu)
    pernyataan_1 = db.Column(Text, nullable=True)
    pernyataan_2 = db.Column(Text, nullable=True)
    pernyataan_3 = db.Column(Text, nullable=True)
    jawaban_1 = db.Column(String(10), nullable=True)
    jawaban_2 = db.Column(String(50), nullable=True)
    jawaban_3 = db.Column(String(50), nullable=True)
    # j

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)


class Ujian(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    nama = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    pelajaran_ujian = relationship(
        "PelajaranUjian", backref="ujian", cascade="all, delete"
    )

    ujian_peserta = relationship("UjianPeserta", backref="ujian", cascade="all, delete")


class PelajaranUjian(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    ujian_id = Column(String(36), ForeignKey("ujian.id", ondelete="CASCADE"))
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    def __str__(self) -> str:
        return self.pelajaran_id


class JadwalUjian(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    ujian_id = Column(String(36), ForeignKey("ujian.id", ondelete="CASCADE"))
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    sesi = Column(String(100))
    tanggal = Column(DateTime)
    durasi = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    ujian_peserta = relationship(
        "UjianPeserta", backref="jadwal_ujian", cascade="all, delete"
    )


class UjianSekolah(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    ujian_id = Column(String(36), ForeignKey("ujian.id", ondelete="CASCADE"))
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    jadwal_ujian_id = Column(
        String(36), ForeignKey("jadwal_ujian.id", ondelete="CASCADE")
    )
    sekolah_id = Column(String(36), ForeignKey("sekolah.id", ondelete="CASCADE"))

    # status = BARU, BERJALAN, SELESAI
    status = Column(String(50), default="BARU", nullable=True)
    kode = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)


class UjianPeserta(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("user.id", ondelete="CASCADE"))
    ujian_id = Column(String(36), ForeignKey("ujian.id", ondelete="CASCADE"))
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    jadwal_ujian_id = Column(
        String(36), ForeignKey("jadwal_ujian.id", ondelete="CASCADE")
    )
    sekolah_id = Column(String(36), ForeignKey("sekolah.id", ondelete="CASCADE"))

    # status = BARU, BERJALAN, SELESAI
    status = Column(String(10), nullable=True, default="BARU")
    hasil = Column(Float, nullable=True)
    waktu_mulai = Column(DateTime, nullable=True)
    waktu_selesai = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)


class Jawaban(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("user.id", ondelete="CASCADE"))
    ujian_id = Column(String(36), ForeignKey("ujian.id", ondelete="CASCADE"))
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    jadwal_ujian_id = Column(
        String(36), ForeignKey("jadwal_ujian.id", ondelete="CASCADE")
    )
    sekolah_id = Column(String(36), ForeignKey("sekolah.id", ondelete="CASCADE"))
    ujian_peserta_id = Column(
        String(36), ForeignKey("ujian_peserta.id", ondelete="CASCADE")
    )
    pertanyaan_id = Column(String(36), ForeignKey("pertanyaan.id", ondelete="CASCADE"))

    # jawaban = Column(String(1), nullable=True)
    jawaban = Column(Text, nullable=True)
    # benar = Column(Boolean, default=False)
    benar = Column(SmallInteger)
    nomor = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)


class Gambar(db.Model):
    id = db.Column(String(36), primary_key=True, default=uuid.uuid4)
    nama = db.Column(String(100))
    data_gambar = db.Column(MEDIUMTEXT)
    pelajaran_id = Column(String(36), ForeignKey("pelajaran.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deleted = Column(Boolean, default=False)

    def __repr__(self):
        return "<image id={},name={}>".format(self.id, self.nama)


class LogError(db.Model):
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("user.id", ondelete="CASCADE"))
    message = Column(String(255))
    traceback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
