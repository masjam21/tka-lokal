from app import db
from app.decorators import role_required
from app.models import Sekolah, User
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

bp = Blueprint("admin", __name__)


@bp.route("/", methods=["GET"])
@login_required
@role_required(roles=["admin"])
def show():
    admin_list: list[User] = (
        User.query.filter(
            User.role.in_(["admin", "pembuat_soal", "proktor"]),
            or_(User.deleted.is_(None), User.deleted != True),
        )
        .order_by(User.username.asc())
        .all()
    )
    return render_template(
        "admin/admin-list.html", title="Admin", admin_list=admin_list
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def add():
    form = {}
    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        name = request.form.get("name")
        password = request.form.get("password")
        role = request.form.get("role")
        school = request.form.get("school")

        if username is None or username == "":
            errors.append("Username tidak boleh kosong")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if password is None or len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        if role is None:
            errors.append("Role tidak boleh kosong")
        elif role not in ["admin", "proktor", "pembuat_soal"]:
            errors.append("Role yang diperbolehkan [admin, proktor, pembuat_soal].")

        if role == "proktor" and school == "":
            errors.append("Sekolah tidak boleh kosong.")

        user_exist = User.query.filter(
            User.username == username, or_(User.deleted.is_(None), User.deleted != True)
        ).first()
        if user_exist is not None:
            errors.append("Username telah terpakai.")

        if len(errors) == 0:
            user: User = User(
                username=username,
                nama=name,
                role=role,
            )

            if role == "proktor":
                user.sekolah_id = school
            else:
                user.sekolah_id = None

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Berhasil menambahkan admin.", "success")
            return redirect(url_for("admin.show"))
        else:
            flash("\\n".join(errors), "error")

    school_list = Sekolah.query.filter(
        or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
    ).all()

    return render_template(
        "admin/admin-form.html",
        title="Tambah Admin",
        form=form,
        id=None,
        school_list=school_list,
    )


@bp.route("/edit/<admin_id>", methods=["GET", "POST"])
@login_required
@role_required(roles=["admin"])
def edit(admin_id):
    user: User = User.query.filter(
        User.id == admin_id, or_(User.deleted.is_(None), User.deleted != True)
    ).first()
    if user is None:
        abort(404)

    form = {
        "username": str(user.username or ""),
        "name": str(user.nama or ""),
        "role": str(user.role or ""),
        "sekolah_id": str(user.sekolah_id or ""),
    }
    errors = []

    if request.method == "POST":
        form = request.form

        username = request.form.get("username")
        name = request.form.get("name")
        password = request.form.get("password")
        role = request.form.get("role")
        school = request.form.get("school")

        if username is None or username == "":
            errors.append("Username tidak boleh kosong")

        if name is None or name == "":
            errors.append("Nama tidak boleh kosong.")

        if password is not None and password != "" and len(password) < 6:
            errors.append("Password harus lebih dari 6 karakter.")

        if role is None:
            errors.append("Role tidak boleh kosong")
        elif role not in ["admin", "proktor", "pembuat_soal"]:
            errors.append("Role yang diperbolehkan [admin, proktor, pembuat_soal].")

        if role == "proktor" and school == "":
            errors.append("Sekolah tidak boleh kosong.")

        user_exist = User.query.filter(
            User.id != admin_id,
            User.username == username,
            or_(User.deleted.is_(None), User.deleted != True),
        ).first()

        if user_exist is not None:
            errors.append("Username telah terpakai.")

        if len(errors) == 0:
            user.username = username
            user.nama = name
            user.role = role

            if role == "proktor":
                user.sekolah_id = school
            else:
                user.sekolah_id = None

            if password is not None and password != "":
                user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Sukses menyimpan ({}).".format(user.username), "success")
            return redirect(url_for("admin.show"))

        else:
            flash("\\n".join(errors), "error")

    school_list = Sekolah.query.filter(
        or_(Sekolah.deleted.is_(None), Sekolah.deleted != True)
    ).all()

    return render_template(
        "admin/admin-form.html",
        title="Edit Admin",
        form=form,
        id=user.id,
        school_list=school_list,
    )


@bp.route("/delete/<admin_id>", methods=["GET"])
@login_required
@role_required(roles=["admin"])
def delete(admin_id):
    admin: User = User.query.filter(
        and_(
            User.id == admin_id,
            or_(
                User.role == "admin",
                User.role == "proktor",
                User.role == "pembuat_soal",
            ),
            or_(User.deleted.is_(None), User.deleted != True),
        )
    ).first()
    if admin is None:
        abort(404)

    if current_user.id == admin.id:
        abort(403)

    # db.session.delete(admin)
    admin.deleted = True

    db.session.commit()

    flash("Berhasil menghapus ({})".format(admin.username), "success")

    return redirect(url_for("admin.show"))
