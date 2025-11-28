import click
from flask.cli import AppGroup

from app import db
from app.models import User

user_cli = AppGroup("user")


@user_cli.command("create-superuser")
@click.option("--username", prompt="Username", help="Username.")
@click.option("--name", prompt="Name", help="Name.")
@click.option(
    "--password",
    prompt="Password",
    help="Password yang digunakan.",
    hide_input=True,
)
def create_user(username, name, password):
    try:
        user = User(username=username, nama=name, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("success create user")
    except Exception as e:
        print(e)


@user_cli.command("reset-password")
@click.option("--username", prompt="Username", help="Username.")
@click.option(
    "--password",
    prompt="Password",
    help="The person to greet.",
    hide_input=True,
)
def create_user(username, password):
    try:
        user: User = User.query.filter_by(username=username).first()
        if user is not None:
            user.set_password(password)
            db.session.commit()
            print("success update user")
        else:
            print("user not found")
    except Exception as e:
        print(e)
