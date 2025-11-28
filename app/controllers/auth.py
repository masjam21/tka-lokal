from app import db
from app.models import User
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if (
        User.query.filter(or_(User.deleted.is_(None), User.deleted != True)).count()
        == 0
    ):
        return redirect(url_for("sync.get_proktor"))

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

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            user: User = User.query.filter(
                User.username == username,
                User.role.in_(["admin", "pembuat_soal", "peserta_didik", "proktor"]),
                or_(User.deleted.is_(None), User.deleted != True),
            ).first()
            if user is None:
                errors.append("Username tidak ditemukan.")
            elif not user.check_password(password):
                errors.append("Password salah.")

            if len(errors) > 0:
                flash("\\n".join(errors), "error")
            else:
                login_user(user)
                flash("Selamat datang.", "success")

                next = request.args.get("next")
                return redirect(next or url_for("index"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = {}
    errors = []
    if request.method == "POST":
        old_password = request.form.get("old_password", default="", type=str)
        new_password = request.form.get("new_password", default="", type=str)
        new_password_confirm = request.form.get(
            "new_password_confirm", default="", type=str
        )

        if old_password == "":
            errors.append("Password Lama tidak boleh kosong.")
        if len(new_password) < 6:
            errors.append("Password baru minimal 6 karakter.")
        if new_password_confirm == "":
            errors.append("Konfirmasi Password Baru tidak boleh kosong.")
        elif new_password != new_password_confirm:
            errors.append("Konfirmasi password tidak sama.")

        if len(errors) > 0:
            flash("\\n".join(errors), "error")
        else:
            user: User = User.query.filter(
                User.id == current_user.id,
                or_(User.deleted.is_(None), User.deleted != True),
            ).first()
            if user is None:
                flash("User tidak ditemukan.", "error")
            elif not user.check_password(old_password):
                flash("Password lama salah.", "error")
            else:
                user.set_password(new_password)
                db.session.commit()
                flash("Berhasil menyimpan password.", "success")

                return redirect(url_for("auth.change_password"))

    return render_template(
        "auth/change-password.html", form=form, title="Ganti Password"
    )
