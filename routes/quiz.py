from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from models import Quiz, Question, Answer, QuizAttempt, UserAnswer, School

quiz_bp = Blueprint("quiz", __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _compute_final_score(raw, max_pts, time_taken_s, time_limit_s):
    """Return final score in [3.0, 10.5]. 10.5 encodes '10+'."""
    if max_pts <= 0:
        return 3.0
    score = max(3.0, (raw / max_pts) * 10)
    if raw >= max_pts and time_taken_s <= time_limit_s * 0.75:
        return 10.5
    return round(score, 1)


def _format_score(value):
    if value is None:
        return "—"
    if value > 10:
        return "10+"
    return f"{value:.1f}".replace(".", ",")


def _school_avg(scores):
    if not scores:
        return None
    top10 = sorted(scores, reverse=True)[:10]
    return sum(top10) / len(top10)


# ── quiz list ─────────────────────────────────────────────────────────────────

@quiz_bp.route("/")
@login_required
def quiz_list():
    quizzes = Quiz.query.filter_by(is_active=True).order_by(Quiz.created_at.desc()).all()
    return render_template("quiz_list.html", quizzes=quizzes)


# ── quiz detail ───────────────────────────────────────────────────────────────

@quiz_bp.route("/<int:quiz_id>")
@login_required
def quiz_detail(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    if not quiz.is_active:
        abort(404)
    best = (
        QuizAttempt.query
        .filter_by(quiz_id=quiz_id, user_id=current_user.id, is_complete=True)
        .order_by(QuizAttempt.final_score.desc(), QuizAttempt.time_taken.asc())
        .first()
    )
    return render_template("quiz_detail.html", quiz=quiz, best=best)


# ── start quiz ────────────────────────────────────────────────────────────────

@quiz_bp.route("/<int:quiz_id>/start", methods=["POST"])
@login_required
def start_quiz(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    if not quiz.is_active:
        abort(404)
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for("quiz.take_quiz", quiz_id=quiz_id, attempt_id=attempt.id))


# ── take quiz ─────────────────────────────────────────────────────────────────

@quiz_bp.route("/<int:quiz_id>/take/<int:attempt_id>")
@login_required
def take_quiz(quiz_id, attempt_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    attempt = db.get_or_404(QuizAttempt, attempt_id)

    if attempt.user_id != current_user.id or attempt.quiz_id != quiz_id:
        abort(403)
    if attempt.is_complete:
        return redirect(url_for("quiz.quiz_result", attempt_id=attempt_id))

    elapsed = (
        datetime.now(timezone.utc) - attempt.started_at.replace(tzinfo=timezone.utc)
    ).total_seconds()
    time_limit_s = quiz.time_limit * 60

    if elapsed >= time_limit_s:
        # time expired: force submit with no answers
        return redirect(
            url_for("quiz.submit_quiz", quiz_id=quiz_id, attempt_id=attempt_id),
            code=307,
        )

    started_ms = int(attempt.started_at.replace(tzinfo=timezone.utc).timestamp() * 1000)
    return render_template(
        "quiz_take.html",
        quiz=quiz,
        attempt=attempt,
        started_ms=started_ms,
        time_limit_s=time_limit_s,
    )


# ── submit quiz ───────────────────────────────────────────────────────────────

@quiz_bp.route("/<int:quiz_id>/submit/<int:attempt_id>", methods=["POST"])
@login_required
def submit_quiz(quiz_id, attempt_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    attempt = db.get_or_404(QuizAttempt, attempt_id)

    if attempt.user_id != current_user.id or attempt.quiz_id != quiz_id:
        abort(403)
    if attempt.is_complete:
        return redirect(url_for("quiz.quiz_result", attempt_id=attempt_id))

    now = datetime.now(timezone.utc)
    time_taken_s = int(
        (now - attempt.started_at.replace(tzinfo=timezone.utc)).total_seconds()
    )
    time_limit_s = quiz.time_limit * 60
    time_taken_s = min(time_taken_s, time_limit_s)

    raw = 0.0
    max_pts = 0.0

    for question in quiz.questions:
        max_pts += question.correct_score
        answer_id_str = request.form.get(f"q{question.id}")

        if not answer_id_str:
            ua = UserAnswer(
                attempt_id=attempt.id, question_id=question.id,
                answer_id=None, is_correct=None, points_earned=0.0,
            )
        else:
            try:
                answer_id = int(answer_id_str)
            except ValueError:
                answer_id = None

            answer = db.session.get(Answer, answer_id) if answer_id else None
            if answer and answer.question_id == question.id:
                pts = float(question.correct_score if answer.is_correct else question.wrong_score)
                raw += pts
                ua = UserAnswer(
                    attempt_id=attempt.id, question_id=question.id,
                    answer_id=answer.id, is_correct=answer.is_correct,
                    points_earned=pts,
                )
            else:
                ua = UserAnswer(
                    attempt_id=attempt.id, question_id=question.id,
                    answer_id=None, is_correct=None, points_earned=0.0,
                )

        db.session.add(ua)

    final = _compute_final_score(raw, max_pts, time_taken_s, time_limit_s)
    attempt.completed_at = now
    attempt.time_taken = time_taken_s
    attempt.raw_score = raw
    attempt.max_score = max_pts
    attempt.final_score = final
    attempt.is_complete = True
    db.session.commit()

    return redirect(url_for("quiz.quiz_result", attempt_id=attempt.id))


# ── result ────────────────────────────────────────────────────────────────────

@quiz_bp.route("/result/<int:attempt_id>")
@login_required
def quiz_result(attempt_id):
    attempt = db.get_or_404(QuizAttempt, attempt_id)
    if attempt.user_id != current_user.id:
        abort(403)

    ua_by_q = {ua.question_id: ua for ua in attempt.user_answers}
    breakdown = []
    for q in attempt.quiz.questions:
        ua = ua_by_q.get(q.id)
        selected = db.session.get(Answer, ua.answer_id) if ua and ua.answer_id else None
        correct_ans = next((a for a in q.answers if a.is_correct), None)
        if ua and ua.is_correct:
            status = "correct"
        elif ua and ua.answer_id:
            status = "wrong"
        else:
            status = "skipped"
        breakdown.append({
            "question": q,
            "selected": selected,
            "correct_answer": correct_ans,
            "points": ua.points_earned if ua else 0.0,
            "status": status,
        })

    return render_template(
        "quiz_result.html",
        attempt=attempt,
        breakdown=breakdown,
    )


# ── history ───────────────────────────────────────────────────────────────────

@quiz_bp.route("/history")
@login_required
def history():
    attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id, is_complete=True)
        .order_by(QuizAttempt.completed_at.desc())
        .all()
    )
    return render_template("quiz_history.html", attempts=attempts)


# ── leaderboard ───────────────────────────────────────────────────────────────

@quiz_bp.route("/<int:quiz_id>/leaderboard")
@login_required
def leaderboard(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)

    all_complete = QuizAttempt.query.filter_by(quiz_id=quiz_id, is_complete=True).all()

    # Best attempt per user (highest score, then fastest)
    best_per_user = {}
    for a in all_complete:
        uid = a.user_id
        prev = best_per_user.get(uid)
        if prev is None or a.final_score > prev.final_score or (
            a.final_score == prev.final_score and a.time_taken < prev.time_taken
        ):
            best_per_user[uid] = a

    global_ranking = sorted(
        best_per_user.values(),
        key=lambda a: (-a.final_score, a.time_taken),
    )

    my_school_ranking = [
        a for a in global_ranking
        if current_user.school_id and a.user.school_id == current_user.school_id
    ]

    # School leaderboard: avg of top-10 per school
    school_scores = {}
    for a in best_per_user.values():
        sid = a.user.school_id
        if sid:
            school_scores.setdefault(sid, []).append(a.final_score)

    school_leaderboard = []
    for sid, scores in school_scores.items():
        school = db.session.get(School, sid)
        if not school:
            continue
        avg = _school_avg(scores)
        school_leaderboard.append({
            "school": school,
            "score": avg,
            "display": _format_score(avg),
            "participants": len(scores),
        })
    school_leaderboard.sort(key=lambda x: (-(x["score"] or 0), x["school"].name))

    return render_template(
        "quiz_leaderboard.html",
        quiz=quiz,
        global_ranking=global_ranking,
        my_school_ranking=my_school_ranking,
        school_leaderboard=school_leaderboard,
        format_score=_format_score,
    )
