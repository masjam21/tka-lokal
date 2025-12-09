import csv
import datetime
import logging
import traceback
import io

from app import db
from app.decorators import role_required
from app.models import RombonganBelajar, Sekolah, User
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, make_response
from flask_login import current_user, login_required
from sqlalchemy import or_

bp = Blueprint("student", __name__)


# --- Helper Function untuk PDF ---
def render_pdf(html_content, filename="document.pdf"):
    """
    Fungsi helper untuk merender HTML menjadi response PDF
    menggunakan WeasyPrint.
    """
    try:
        from weasyprint import HTML
        
        # Render PDF ke memory buffer
        pdf_io = io.BytesIO()
        # base_url=request.host_url penting agar gambar/css lokal terbaca
        HTML(string=html_content, base_url=request.host_url).write_pdf(target=pdf_io)
        pdf_io.seek(0)
        
        response = make_response(pdf_io.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    except ImportError:
        return "Library 'weasyprint' belum terinstall. Mohon jalankan: pip install weasyprint", 500
    except Exception as e:
        logging.error(traceback.format_exc())
        return f"Terjadi kesalahan saat generate PDF: {str(e)}", 500


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
        if school == "all":
            filter_query = [
                User.role == "peserta_didik",
                or_(
                    User.deleted.is_(None),
                    or_(User.deleted.is_(None), User.deleted != True),
                ),
            ]
        else:
            filter_query = [
                User.role == "peserta_didik",
                User.sekolah_id == school,
                or_(
                    User.deleted.is_(None),
                    or_(User.deleted.is_(None), User.deleted != True),
                ),
            ]

        student_list = (
            User.query.filter(*filter_query).order_by(User.nama.asc()).all()
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
@role_required(roles=["admin", "proktor"])
def add():
    # Jika proktor, batasi operasi pada sekolah milik proktor
    school = request.args.get("school", default="", type=str)

    if current_user.role == "proktor":
        # override sekolah agar proktor hanya dapat menambah untuk sekolahnya
        school = current_user.sekolah_id

    form = {"sekolah_id": school}
    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        name = request.form.get("nama")
        password = request.form.get("password")
        sekolah_id = request.form.get("sekolah_id")
        # jika proktor, pastikan sekolah_id yang dipakai adalah sekolah proktor
        if current_user.role == "proktor":
            sekolah_id = current_user.sekolah_id
        nis = request.form.get("nis")
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

            user.nis = nis
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
            flash("\n".join(errors), "error")

    # Jika proktor, hanya tampilkan sekolah milik proktor pada daftar sekolah
    if current_user.role == "proktor":
        school_list = (
            Sekolah.query.filter(
                Sekolah.id == current_user.sekolah_id,
                or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
            )
            .order_by(Sekolah.nama.asc())
            .all()
        )
    else:
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
@role_required(roles=["admin", "proktor"])
def edit(student_id):
    user: User = User.query.filter(
        User.id == student_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()
    if user is None:
        abort(404)

    # proktor hanya boleh mengedit peserta dari sekolahnya
    if current_user.role == "proktor" and user.sekolah_id != current_user.sekolah_id:
        abort(403)

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
        nis = request.form.get("nis")
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

        # jika proktor, paksa sekolah sesuai proktor (hindari spoofing)
        if current_user.role == "proktor":
            sekolah_id = current_user.sekolah_id

        if rombongan_belajar_id is None or rombongan_belajar_id == "":
            errors.append("Rombongan Belajar tidak boleh kosong.")
        else:
            # pastikan rombongan_belajar milik sekolah yang dipilih
            rombel_obj = RombonganBelajar.query.filter(
                RombonganBelajar.id == rombongan_belajar_id,
                RombonganBelajar.sekolah_id == sekolah_id,
                or_(RombonganBelajar.deleted.is_(None), RombonganBelajar.deleted != True),
            ).first()
            if rombel_obj is None:
                errors.append("Rombongan Belajar tidak ditemukan untuk sekolah yang dipilih.")

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

            user.nis = nis
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
            flash("\n".join(errors), "error")

    # Jika proktor, batasi daftar sekolah hanya ke sekolah milik proktor
    if current_user.role == "proktor":
        school_list = (
            Sekolah.query.filter(
                Sekolah.id == current_user.sekolah_id,
                or_(Sekolah.deleted.is_(None), Sekolah.deleted != True),
            )
            .order_by(Sekolah.nama.asc())
            .all()
        )
    else:
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


@bp.route('/print/<student_id>', methods=['GET'])
@login_required
@role_required(roles=["admin", "proktor", "helpdesk"])
def print_card(student_id):
    # Ini untuk Print Tampilan Web (HTML biasa)
    student: User = User.query.filter(
        User.id == student_id,
        User.role == 'peserta_didik',
        or_(User.deleted.is_(None), User.deleted != True),
    ).first()
    if student is None:
        abort(404)

    return render_template('student/kartu.html', student=student)


# --- RUTE BARU: Print Satuan ke PDF ---
@bp.route('/print/<student_id>/pdf', methods=['GET'])
@login_required
@role_required(roles=["admin", "proktor", "helpdesk"])
def print_card_pdf(student_id):
    student: User = User.query.filter(
        User.id == student_id,
        User.role == 'peserta_didik',
        or_(User.deleted.is_(None), User.deleted != True),
    ).first()
    
    if student is None:
        abort(404)

    # Render template HTML khusus PDF
    waktu_cetak = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    # Dibungkus dalam list [student] agar bisa menggunakan template looping yang sama dengan bulk
    html = render_template('student/kartu_pdf.html', students=[student])
    
    filename = f"Kartu_{student.username}.pdf"
    return render_pdf(html, filename)


@bp.route('/print_bulk', methods=['GET'])
@login_required
@role_required(roles=["admin", "proktor", "helpdesk"])
def print_bulk():
    # Ini untuk Print Bulk Tampilan Web (HTML biasa)
    ids = request.args.get('ids', '')
    include_password = request.args.get('include_password', '0') == '1'
    if ids == '':
        abort(400)
    id_list = [i for i in ids.split(',') if i]
    students = (
        User.query.filter(
            User.id.in_(id_list), User.role == 'peserta_didik',
            or_(User.deleted.is_(None), User.deleted != True),
        )
        .order_by(User.nama.asc())
        .all()
    )

    # group into pages of 10 (2 columns x 5 rows)
    
    waktu_cetak = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    return render_template('student/kartu_bulk.html', pages=pages, include_password=include_password)


# --- RUTE UPDATE: Print Bulk ke PDF ---
@bp.route('/print_bulk_pdf', methods=['GET'])
@login_required
@role_required(roles=["admin", "proktor", "helpdesk"])
def print_bulk_pdf():
    ids = request.args.get('ids', '')
    # include_password belum dipakai di template PDF sederhana, bisa ditambahkan jika perlu
    
    if ids == '':
        abort(400)
        
    id_list = [i for i in ids.split(',') if i]
    students = (
        User.query.filter(
            User.id.in_(id_list), User.role == 'peserta_didik',
            or_(User.deleted.is_(None), User.deleted != True),
        )
        .order_by(User.nama.asc())
        .all()
    )

    pages = [students[i : i + 10] for i in range(0, len(students), 10)]# Gunakan template kartu_pdf.html yang sudah disiapkan
    html = render_template('student/kartu_pdf.html', students=students)
    
    return render_pdf(html, "Kartu_Peserta_Massal.pdf")


@bp.route("/import", methods=["GET", "POST"])
@login_required
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
            flash("\n".join(errors), "error")

    return render_template(
        "student/student-import.html", title="Import Peserta", form=form
    )


@bp.route("logged-out/<student_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["proktor", "admin"])
def logged_out(student_id):
    student: User = User.query.filter(
        User.id == student_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()

    if student is None:
        abort(404)

    student.is_logged_in = False
    db.session.commit()

    flash("Logout peserta berhasil.", "success")

    return redirect(url_for("student.show"))