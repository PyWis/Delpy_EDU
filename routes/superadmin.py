from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from models import School, User

superadmin_bp = Blueprint("superadmin", __name__)


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin():
            flash("Accesso riservato al superamministratore.", "danger")
            return redirect(url_for("auth.dashboard"))
        return f(*args, **kwargs)
    return decorated


@superadmin_bp.route("/schools")
@login_required
@superadmin_required
def schools():
    all_schools = School.query.order_by(School.created_at.desc()).all()
    return render_template("superadmin/schools.html", schools=all_schools)


@superadmin_bp.route("/schools/<int:school_id>/users")
@login_required
@superadmin_required
def school_users(school_id):
    school = db.get_or_404(School, school_id)
    users = (
        User.query
        .filter_by(school_id=school_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return render_template("superadmin/school_users.html", school=school, users=users)


@superadmin_bp.route("/schools/<int:school_id>/verify", methods=["POST"])
@login_required
@superadmin_required
def toggle_school_verification(school_id):
    school = db.get_or_404(School, school_id)
    school.is_verified = not school.is_verified
    db.session.commit()
    status = "verificata" if school.is_verified else "non verificata"
    flash(f"Scuola '{school.name}' {status}.", "success")
    return redirect(url_for("superadmin.schools"))


@superadmin_bp.route("/schools/<int:school_id>/delete", methods=["POST"])
@login_required
@superadmin_required
def delete_school(school_id):
    school = db.get_or_404(School, school_id)
    name = school.name
    db.session.delete(school)
    db.session.commit()
    flash(f"Scuola '{name}' e tutti i suoi utenti eliminati.", "success")
    return redirect(url_for("superadmin.schools"))


@superadmin_bp.route("/schools/<int:school_id>/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@superadmin_required
def toggle_user(school_id, user_id):
    user = db.get_or_404(User, user_id)
    if user.school_id != school_id:
        flash("Non autorizzato.", "danger")
        return redirect(url_for("superadmin.school_users", school_id=school_id))
    user.is_active = not user.is_active
    db.session.commit()
    status = "abilitato" if user.is_active else "disabilitato"
    flash(f"Utente '{user.username}' {status}.", "success")
    return redirect(url_for("superadmin.school_users", school_id=school_id))


@superadmin_bp.route("/schools/<int:school_id>/users/<int:user_id>/delete", methods=["POST"])
@login_required
@superadmin_required
def delete_user(school_id, user_id):
    user = db.get_or_404(User, user_id)
    if user.school_id != school_id:
        flash("Non autorizzato.", "danger")
        return redirect(url_for("superadmin.school_users", school_id=school_id))
    name = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Utente '{name}' eliminato.", "success")
    return redirect(url_for("superadmin.school_users", school_id=school_id))
