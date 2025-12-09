import csv

from sqlalchemy import delete

from app import db
from app.decorators import role_required
from app.models import Jawaban, Pelajaran, Pertanyaan
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

bp = Blueprint("question", __name__)


@bp.route("/<lesson_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def show(lesson_id):
    lesson: Pelajaran = Pelajaran.query.filter(
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
        Pelajaran.id == lesson_id,
    ).first()
    if not lesson:
        abort(404)
    question = (
        Pertanyaan.query.filter(
            Pertanyaan.pelajaran_id == lesson.id,
            or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
        )
        .order_by(Pertanyaan.id.desc())
        .all()
    )
    question_list = []
    for i in question:
        ll = i.__dict__
        ll["jawaban_A"] = 0
        ll["jawaban_B"] = 0
        ll["jawaban_C"] = 0
        ll["jawaban_D"] = 0
        # ll["jawaban_E"] = 0
        ll["total"] = 0
        ll["jawaban_benar"] = 0

        jawaban = Jawaban.query.filter(Jawaban.pertanyaan_id == i.id).all()
        for j in jawaban:
            ll["total"] += 1
            if j.jawaban is not None:
                ll[f"jawaban_{j.jawaban}"] += 1
            if j.benar:
                ll["jawaban_benar"] += 1

        # tampilkan multi-jawaban (ceklis) agar rapi
        if ll.get("tipe_pertanyaan") == "ceklis" and ll.get("jawaban"):
            parts = [p.strip() for p in ll["jawaban"].split(",") if p.strip()]
            ll["jawaban_display"] = ", ".join(parts)
        else:
            ll["jawaban_display"] = ll.get("jawaban")

        question_list.append(ll)

    return render_template(
        "question/question-list.html",
        title="Pertanyaan",
        question_list=question_list,
        lesson=lesson,
    )


@bp.route("/<lesson_id>/add", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def add(lesson_id):
    lesson: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if not lesson:
        abort(404)

    form = lesson.__dict__
    errors = []

    if request.method == "POST":
        form = request.form
        question = request.form.get("pertanyaan", default="", type=str)
        count = request.form.get("jumlah_pilihan", default=0, type=int)

        option = []
        option.append(request.form.get("pilihan_a"))
        option.append(request.form.get("pilihan_b"))
        option.append(request.form.get("pilihan_c"))
        option.append(request.form.get("pilihan_d"))
        # option.append(request.form.get("pilihan_e"))

        answer = request.form.get("jawaban", default="", type=str)

        if question == "":
            errors.append("Pertanyaan tidak boleh kosong.")

        if int(count) < 1 or int(count) > 5:
            errors.append("Jumlah Jawaban harus 1 - 5.")
        else:
            for i in range(int(count)):
                if option[i] is None or option[i] == "":
                    errors.append(
                        "Jawaban {} tidak boleh kosong.".format(
                            ["A", "B", "C", "D", "E"][i]
                        )
                    )

        if answer not in ["A", "B", "C", "D", "E"]:
            errors.append("Jawaban harus A B C D E.")

        if len(errors) == 0:
            question_obj = Pertanyaan(
                pelajaran_id=lesson.id,
                pertanyaan=question,
                jumlah_pilihan=int(count),
                tipe_pertanyaan="pilihan_ganda",
                pilihan_a=option[0],
                pilihan_b=option[1] if int(count) > 1 else None,
                pilihan_c=option[2] if int(count) > 2 else None,
                pilihan_d=option[3] if int(count) > 3 else None,
                pilihan_e=option[4] if int(count) > 4 else None,
                jawaban=answer,
            )

            db.session.add(question_obj)
            db.session.commit()

            flash("Berhasil menyimpan pertanyaan", "success")

            return redirect(url_for("lesson.question.show", lesson_id=lesson.id))
        else:
            flash("\\n".join(errors), "error")

    return render_template(
        "question/question-form.html",
        title="Tambah Pertanyaan",
        form=form,
        id=None,
        lesson=lesson,
    )


@bp.route("<lesson_id>/edit/<question_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def edit(lesson_id, question_id):
    lesson: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if not lesson:
        abort(404)

    question_obj: Pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == question_id,
        Pertanyaan.pelajaran_id == lesson_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if not question_obj:
        abort(404)

    form = question_obj.__dict__
    errors = []

    if request.method == "POST":
        form = request.form
        question = request.form.get("pertanyaan", default="", type=str)
        count = request.form.get("jumlah_pilihan", default=0, type=int)

        option = []
        option.append(request.form.get("pilihan_a"))
        option.append(request.form.get("pilihan_b"))
        option.append(request.form.get("pilihan_c"))
        option.append(request.form.get("pilihan_d"))
        # option.append(request.form.get("pilihan_e"))

        answer = request.form.get("jawaban", default="", type=str)

        if question == "":
            errors.append("Pertanyaan tidak boleh kosong.")

        if int(count) < 1 or int(count) > 5:
            errors.append("Jumlah Jawaban harus 1 - 5.")
        else:
            for i in range(int(count)):
                if option[i] is None or option[i] == "":
                    errors.append(
                        "Jawaban {} tidak boleh kosong.".format(
                            ["A", "B", "C", "D", "E"][i]
                        )
                    )

        if answer not in ["A", "B", "C", "D", "E"]:
            errors.append("Jawaban harus A B C D E.")

        if len(errors) == 0:
            question_obj.pertanyaan = question
            question_obj.jumlah_pilihan = int(count)
            question_obj.pilihan_a = option[0]
            question_obj.pilihan_b = option[1] if int(count) > 1 else None
            question_obj.pilihan_c = option[2] if int(count) > 2 else None
            question_obj.pilihan_d = option[3] if int(count) > 3 else None
            # question_obj.pilihan_e = option[4] if int(count) > 4 else None
            question_obj.jawaban = answer

            db.session.commit()

            flash("Berhasil menyimpan pertanyaan", "success")
            return redirect(url_for("lesson.question.show", lesson_id=lesson.id))
        else:
            flash("\\n".join(errors), "error")

    return render_template(
        "question/question-form.html",
        title="Edit Pertanyaan",
        form=form,
        id=question_id,
        lesson=lesson,
    )


@bp.route("<lesson_id>/delete/<question_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def delete(lesson_id, question_id):
    lesson: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if not lesson:
        abort(404)

    question_obj: Pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == question_id,
        Pertanyaan.pelajaran_id == lesson_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if not question_obj:
        abort(404)

    question_obj.deleted = True
    db.session.commit()

    flash("Berhasil menghapus pertanyaan", "success")

    return redirect(url_for("lesson.question.show", lesson_id=lesson.id))


@bp.route("<lesson_id>/import", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def import_(lesson_id):

    lesson: Pelajaran = Pelajaran.query.get(lesson_id)
    if not lesson:
        abort(404)

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

                if "pertanyaan" in row and "jawaban" in row and "jumlah_pilihan" in row:
                    question = row["pertanyaan"]
                    if row["jawaban"] in ["A", "B", "C", "D", "E"]:
                        answer = row["jawaban"]
                        if (
                            row["jumlah_pilihan"].isdigit()
                            and int(row["jumlah_pilihan"]) > 0
                            and int(row["jumlah_pilihan"]) <= 5
                        ):
                            option_count = int(row["jumlah_pilihan"])
                            options = [None, None, None, None, None]
                            option_list = ["a", "b", "c", "d", "e"]
                            for i in range(option_count):
                                op = "pilihan_{}".format(option_list[i])
                                if op in row:
                                    options[i] = row[op]

                    question_obj = Pertanyaan(
                        pelajaran_id=lesson.id,
                        pertanyaan=question,
                        jumlah_pilihan=int(option_count),
                        tipe_pertanyaan="pilihan_jawaban",
                        pilihan_a=options[0],
                        pilihan_b=options[1] if int(option_count) > 1 else None,
                        pilihan_c=options[2] if int(option_count) > 2 else None,
                        pilihan_d=options[3] if int(option_count) > 3 else None,
                        pilihan_e=options[4] if int(option_count) > 4 else None,
                        jawaban=answer,
                    )

                    db.session.add(question_obj)

            db.session.commit()

            flash("Berhasil import pertanyaan", "success")

            return redirect(url_for("lesson.question.show", lesson_id=lesson.id))

        else:
            flash("\\n".join(errors), "error")

    return render_template(
        "question/question-import.html",
        title="Import Pertanyaan",
        form=form,
        lesson=lesson,
    )


@bp.route("/<lesson_id>/preview/<question_id>", methods=["GET"])
@login_required
@role_required(roles=["admin", "pembuat_soal"])
def preview(lesson_id, question_id):
    lesson: Pelajaran = Pelajaran.query.filter(
        Pelajaran.id == lesson_id,
        or_(Pelajaran.deleted.is_(None), Pelajaran.deleted != True),
    ).first()
    if not lesson:
        abort(404)

    pertanyaan = Pertanyaan.query.filter(
        Pertanyaan.id == question_id,
        or_(Pertanyaan.deleted.is_(None), Pertanyaan.deleted != True),
    ).first()
    if pertanyaan is None:
        abort(404)

    return render_template(
        "question/question-preview.html",
        title="Ujian",
        pertanyaan=pertanyaan,
    )
