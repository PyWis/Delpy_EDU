import secrets
import string

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from models import User
from email_service import send_welcome_email

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Accesso riservato all'amministratore della scuola.", "danger")
            return redirect(url_for("auth.dashboard"))
        return f(*args, **kwargs)

    return decorated


def _generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@admin_bp.route("/users")
@login_required
@admin_required
def user_list():
    users = (
        User.query
        .filter_by(school_id=current_user.school_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template("users.html", users=users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "student")

        if not username or not email:
            flash("Nome utente ed email sono obbligatori.", "danger")
            return render_template("create_user.html")

        if role not in ("admin", "student"):
            role = "student"

        if User.query.filter_by(email=email).first():
            flash("Questa email è già registrata.", "danger")
            return render_template("create_user.html")

        temp_password = _generate_temp_password()
        user = User(
            school_id=current_user.school_id,
            username=username,
            email=email,
            role=role,
        )
        user.set_password(temp_password)
        db.session.add(user)
        db.session.commit()

        sent = send_welcome_email(
            email, username, current_user.school.name, temp_password
        )

        if sent:
            flash(f"Utente {username} creato. Email di benvenuto inviata.", "success")
        else:
            flash(
                f"Utente {username} creato. Password temporanea: {temp_password} "
                "(invio email fallito — comunicala manualmente).",
                "warning",
            )

        return redirect(url_for("admin.user_list"))

    return render_template("create_user.html")


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.school_id != current_user.school_id:
        flash("Non autorizzato.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.id == current_user.id:
        flash("Non puoi disabilitare il tuo stesso account.", "danger")
        return redirect(url_for("admin.user_list"))

    user.is_active = not user.is_active
    db.session.commit()
    status = "abilitato" if user.is_active else "disabilitato"
    flash(f"Utente {user.username} {status}.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.school_id != current_user.school_id:
        flash("Non autorizzato.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.id == current_user.id:
        flash("Non puoi eliminare il tuo stesso account.", "danger")
        return redirect(url_for("admin.user_list"))

    db.session.delete(user)
    db.session.commit()
    flash(f"Utente {user.username} eliminato.", "success")
    return redirect(url_for("admin.user_list"))
