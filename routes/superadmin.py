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


# ── SCUOLE ────────────────────────────────────────────────────────────────────

@superadmin_bp.route("/schools")
@login_required
@superadmin_required
def schools():
    all_schools = School.query.order_by(School.created_at.desc()).all()
    return render_template("superadmin/schools.html", schools=all_schools)


@superadmin_bp.route("/schools/create", methods=["GET", "POST"])
@login_required
@superadmin_required
def create_school():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        verified = request.form.get("is_verified") == "1"

        if not name or not email or not password:
            flash("Nome, email e password sono obbligatori.", "danger")
            return render_template("superadmin/school_form.html", school=None)

        if len(password) < 8:
            flash("La password deve essere di almeno 8 caratteri.", "danger")
            return render_template("superadmin/school_form.html", school=None)

        if School.query.filter_by(email=email).first():
            flash("Questa email è già registrata da un'altra scuola.", "danger")
            return render_template("superadmin/school_form.html", school=None)

        if User.query.filter_by(email=email).first():
            flash("Questa email è già in uso da un utente.", "danger")
            return render_template("superadmin/school_form.html", school=None)

        school = School(name=name, email=email, is_verified=verified)
        school.set_password(password)
        db.session.add(school)
        db.session.flush()  # ottieni school.id prima del commit

        admin = User(school_id=school.id, username=name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        flash(f"Scuola '{name}' creata con utente admin '{email}'.", "success")
        return redirect(url_for("superadmin.schools"))

    return render_template("superadmin/school_form.html", school=None)


@superadmin_bp.route("/schools/<int:school_id>/edit", methods=["GET", "POST"])
@login_required
@superadmin_required
def edit_school(school_id):
    school = db.get_or_404(School, school_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        verified = request.form.get("is_verified") == "1"

        if not name or not email:
            flash("Nome ed email sono obbligatori.", "danger")
            return render_template("superadmin/school_form.html", school=school)

        conflict = School.query.filter(School.email == email, School.id != school_id).first()
        if conflict:
            flash("Questa email è già in uso da un'altra scuola.", "danger")
            return render_template("superadmin/school_form.html", school=school)

        school.name = name
        school.email = email
        school.is_verified = verified

        if password:
            if len(password) < 8:
                flash("La nuova password deve essere di almeno 8 caratteri.", "danger")
                return render_template("superadmin/school_form.html", school=school)
            school.set_password(password)

        db.session.commit()
        flash(f"Scuola '{name}' aggiornata.", "success")
        return redirect(url_for("superadmin.schools"))

    return render_template("superadmin/school_form.html", school=school)


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


# ── UTENTI ────────────────────────────────────────────────────────────────────

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


@superadmin_bp.route("/schools/<int:school_id>/users/create", methods=["GET", "POST"])
@login_required
@superadmin_required
def create_user(school_id):
    school = db.get_or_404(School, school_id)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "student")
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Nome, email e password sono obbligatori.", "danger")
            return render_template("superadmin/user_form.html", school=school, user=None)

        if len(password) < 8:
            flash("La password deve essere di almeno 8 caratteri.", "danger")
            return render_template("superadmin/user_form.html", school=school, user=None)

        if role not in ("admin", "student"):
            role = "student"

        if User.query.filter_by(email=email).first():
            flash("Questa email è già in uso.", "danger")
            return render_template("superadmin/user_form.html", school=school, user=None)

        user = User(school_id=school_id, username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f"Utente '{username}' creato.", "success")
        return redirect(url_for("superadmin.school_users", school_id=school_id))

    return render_template("superadmin/user_form.html", school=school, user=None)


@superadmin_bp.route("/schools/<int:school_id>/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@superadmin_required
def edit_user(school_id, user_id):
    school = db.get_or_404(School, school_id)
    user = db.get_or_404(User, user_id)

    if user.school_id != school_id:
        flash("Non autorizzato.", "danger")
        return redirect(url_for("superadmin.school_users", school_id=school_id))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "student")
        is_active = request.form.get("is_active") == "1"
        password = request.form.get("password", "")

        if not username or not email:
            flash("Nome ed email sono obbligatori.", "danger")
            return render_template("superadmin/user_form.html", school=school, user=user)

        if role not in ("admin", "student"):
            role = "student"

        conflict = User.query.filter(User.email == email, User.id != user_id).first()
        if conflict:
            flash("Questa email è già in uso da un altro utente.", "danger")
            return render_template("superadmin/user_form.html", school=school, user=user)

        user.username = username
        user.email = email
        user.role = role
        user.is_active = is_active

        if password:
            if len(password) < 8:
                flash("La nuova password deve essere di almeno 8 caratteri.", "danger")
                return render_template("superadmin/user_form.html", school=school, user=user)
            user.set_password(password)

        db.session.commit()
        flash(f"Utente '{username}' aggiornato.", "success")
        return redirect(url_for("superadmin.school_users", school_id=school_id))

    return render_template("superadmin/user_form.html", school=school, user=user)


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
