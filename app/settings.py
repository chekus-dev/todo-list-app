from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, logout_user

from .extensions import db
from .models import User

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/")
@login_required
def index():
    return render_template("settings.html")


@bp.route("/theme", methods=["POST"])
@login_required
def theme():
    choice = request.form.get("theme")
    if choice in ("dark", "light"):
        current_user.theme = choice
        db.session.commit()
    return redirect(request.referrer or url_for("settings.index"))


@bp.route("/email", methods=["POST"])
@login_required
def update_email():
    new_email = request.form.get("email", "").strip().lower()
    password = request.form.get("current_password", "")

    if not current_user.check_password(password):
        flash("Current password is incorrect.", "error")
    elif not new_email:
        flash("Email cannot be empty.", "error")
    elif new_email != current_user.email and User.query.filter_by(email=new_email).first():
        flash("That email is already in use.", "error")
    else:
        current_user.email = new_email
        db.session.commit()
        flash("Email updated.", "success")

    return redirect(url_for("settings.index"))


@bp.route("/password", methods=["POST"])
@login_required
def update_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current password is incorrect.", "error")
    elif len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
    elif new_password != confirm_password:
        flash("New passwords don't match.", "error")
    else:
        current_user.set_password(new_password)
        db.session.commit()
        flash("Password updated.", "success")

    return redirect(url_for("settings.index"))


@bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    password = request.form.get("current_password", "")

    if not current_user.check_password(password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("settings.index"))

    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.home"))
