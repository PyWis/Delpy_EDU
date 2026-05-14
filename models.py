from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class School(db.Model):
    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    token_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    users = db.relationship("User", backref="school", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<School {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="student")  # "superadmin", "admin" or "student"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    quiz_results = db.relationship("QuizResult", backref="user", lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship("QuizAttempt", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def is_superadmin(self):
        return self.role == "superadmin"

    def __repr__(self):
        return f"<User {self.username}>"


# ── Legacy quiz results (CSV-based, kept for backward compat) ─────────────────

class QuizResult(db.Model):
    __tablename__ = "quiz_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_filename = db.Column(db.String(200), nullable=False)
    quiz_title = db.Column(db.String(200))
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def percentage(self):
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100)


# ── New quiz system ───────────────────────────────────────────────────────────

class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit = db.Column(db.Integer, nullable=False)  # minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    questions = db.relationship(
        "Question", backref="quiz", lazy=True,
        cascade="all, delete-orphan", order_by="Question.order"
    )
    attempts = db.relationship("QuizAttempt", backref="quiz", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz {self.title}>"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    correct_score = db.Column(db.Integer, default=1)  # 1–5
    wrong_score = db.Column(db.Integer, default=0)    # 0 or -1

    answers = db.relationship(
        "Answer", backref="question", lazy=True, cascade="all, delete-orphan"
    )


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    time_taken = db.Column(db.Integer)   # seconds
    raw_score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float)   # 3.0–10.5  (10.5 = "10+")
    is_complete = db.Column(db.Boolean, default=False)

    user_answers = db.relationship(
        "UserAnswer", backref="attempt", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def display_score(self):
        if self.final_score is None:
            return "—"
        if self.final_score > 10:
            return "10+"
        return f"{self.final_score:.1f}".replace(".", ",")

    @property
    def display_time(self):
        if self.time_taken is None:
            return "—"
        m, s = divmod(self.time_taken, 60)
        return f"{m}:{s:02d}"


class UserAnswer(db.Model):
    __tablename__ = "user_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey("answers.id"), nullable=True)  # null = skipped
    is_correct = db.Column(db.Boolean)   # null = skipped
    points_earned = db.Column(db.Float, default=0.0)
