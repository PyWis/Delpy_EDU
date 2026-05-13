import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from models import School, User
from email_service import send_verification_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return render_template("index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        school_name = request.form.get("school_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not school_name or not email or not password:
            flash("Tutti i campi sono obbligatori.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Le password non coincidono.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("La password deve essere di almeno 8 caratteri.", "danger")
            return render_template("register.html")

        if School.query.filter_by(email=email).first():
            flash("Questa email è già registrata.", "danger")
            return render_template("register.html")

        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)

        school = School(
            name=school_name,
            email=email,
            verification_token=token,
            token_expiry=expiry,
        )
        school.set_password(password)
        db.session.add(school)
        db.session.flush()

        admin_user = User(
            school_id=school.id,
            username=school_name,
            email=email,
            role="admin",
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()

        verify_url = url_for("auth.verify_email", token=token, _external=True)
        sent = send_verification_email(email, school_name, verify_url)

        if sent:
            flash("Registrazione completata! Controlla la tua email per verificare l'account.", "success")
        else:
            flash("Registrazione completata! (Invio email fallito — controlla la configurazione BREVO.)", "warning")

        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/verify/<token>")
def verify_email(token):
    school = School.query.filter_by(verification_token=token).first()

    if not school:
        flash("Link di verifica non valido.", "danger")
        return redirect(url_for("auth.login"))

    now = datetime.now(timezone.utc)
    expiry = school.token_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if now > expiry:
        flash("Il link di verifica è scaduto. Contatta l'amministratore.", "danger")
        return redirect(url_for("auth.login"))

    school.is_verified = True
    school.verification_token = None
    school.token_expiry = None
    db.session.commit()

    flash("Email verificata con successo! Puoi ora accedere.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Email o password errati.", "danger")
            return render_template("login.html")

        if not user.is_active:
            flash("Account disabilitato. Contatta l'amministratore della scuola.", "danger")
            return render_template("login.html")

        if not user.school.is_verified:
            flash("L'account della scuola non è ancora verificato. Controlla la tua email.", "warning")
            return render_template("login.html")

        login_user(user, remember=False)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("auth.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Disconnesso con successo.", "info")
    return redirect(url_for("auth.index"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    from quiz_loader import get_quiz_list
    from models import QuizResult
    quizzes = get_quiz_list()
    recent_results = (
        QuizResult.query
        .filter_by(user_id=current_user.id)
        .order_by(QuizResult.completed_at.desc())
        .limit(5)
        .all()
    )
    school_users = []
    if current_user.is_admin():
        school_users = User.query.filter_by(school_id=current_user.school_id).all()
    return render_template(
        "dashboard.html",
        quizzes=quizzes,
        recent_results=recent_results,
        school_users=school_users,
    )
