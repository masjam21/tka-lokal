from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app, db
from app.models import Sekolah, RombonganBelajar, Pelajaran, Ujian, PelajaranUjian, JadwalUjian, User, UjianPeserta
import datetime


def get_or_create(model, filter_kwargs, create_kwargs=None):
    obj = model.query.filter_by(**filter_kwargs).first()
    if obj:
        return obj, False
    params = dict(filter_kwargs)
    if create_kwargs:
        params.update(create_kwargs)
    obj = model(**params)
    db.session.add(obj)
    db.session.flush()
    return obj, True


def main():
    app = create_app()
    with app.app_context():
        # Sekolah
        sekolah, created = get_or_create(Sekolah, {"nama": "Test School"}, {"npsn": "000000"})

        # Rombongan Belajar
        rombel, _ = get_or_create(
            RombonganBelajar,
            {"sekolah_id": sekolah.id, "nama": "Kelas Test"},
            {"tingkat_pendidikan": "10"},
        )

        # Pelajaran
        pelajaran, _ = get_or_create(Pelajaran, {"nama": "Matematika"}, {"kode": "MATH01"})

        # Ujian
        ujian, _ = get_or_create(Ujian, {"nama": "Ujian Demo"})

        # PelajaranUjian link
        pu = PelajaranUjian.query.filter_by(ujian_id=ujian.id, pelajaran_id=pelajaran.id).first()
        if not pu:
            pu = PelajaranUjian(ujian_id=ujian.id, pelajaran_id=pelajaran.id)
            db.session.add(pu)

        # Jadwal Ujian
        jadwal = JadwalUjian.query.filter_by(ujian_id=ujian.id, pelajaran_id=pelajaran.id).first()
        if not jadwal:
            jadwal = JadwalUjian(
                ujian_id=ujian.id,
                pelajaran_id=pelajaran.id,
                sesi="1",
                tanggal=datetime.datetime.now() - datetime.timedelta(days=1),
                durasi=60,
            )
            db.session.add(jadwal)

        # Create a test peserta user
        user = User.query.filter_by(username="test_student1").first()
        if not user:
            user = User(
                username="test_student1",
                nama="Test Student",
                role="peserta_didik",
                sekolah_id=sekolah.id,
                rombongan_belajar_id=rombel.id,
            )
            user.set_password("password123")
            db.session.add(user)

        db.session.commit()

        # Create UjianPeserta
        up = UjianPeserta.query.filter_by(user_id=user.id, ujian_id=ujian.id, jadwal_ujian_id=jadwal.id).first()
        if not up:
            up = UjianPeserta(
                user_id=user.id,
                ujian_id=ujian.id,
                pelajaran_id=pelajaran.id,
                jadwal_ujian_id=jadwal.id,
                sekolah_id=sekolah.id,
                status="BARU",
            )
            db.session.add(up)

        db.session.commit()

        print("Created/Test data:")
        print("  Sekolah:", sekolah.id, sekolah.nama)
        print("  Rombel:", rombel.id, rombel.nama)
        print("  Pelajaran:", pelajaran.id, pelajaran.nama)
        print("  Ujian:", ujian.id, ujian.nama)
        print("  Jadwal:", jadwal.id, "sesi", jadwal.sesi)
        print("  User:", user.id, user.username)
        print("  UjianPeserta:", up.id)


if __name__ == "__main__":
    main()
