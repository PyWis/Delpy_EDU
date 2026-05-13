from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from models import QuizResult
from quiz_loader import get_quiz_list, load_quiz

quiz_bp = Blueprint("quiz", __name__)


@quiz_bp.route("/")
@login_required
def quiz_list():
    quizzes = get_quiz_list()
    return render_template("quiz_list.html", quizzes=quizzes)


@quiz_bp.route("/<filename>")
@login_required
def take_quiz(filename):
    if not filename.endswith(".csv"):
        flash("Quiz non trovato.", "danger")
        return redirect(url_for("quiz.quiz_list"))

    questions = load_quiz(filename)
    if questions is None:
        flash("Quiz non trovato.", "danger")
        return redirect(url_for("quiz.quiz_list"))

    title = filename.replace("_", " ").replace("-", " ").rsplit(".", 1)[0].title()
    return render_template("quiz.html", filename=filename, title=title, questions=questions)


@quiz_bp.route("/<filename>/submit", methods=["POST"])
@login_required
def submit_quiz(filename):
    if not filename.endswith(".csv"):
        flash("Quiz non valido.", "danger")
        return redirect(url_for("quiz.quiz_list"))

    questions = load_quiz(filename)
    if questions is None:
        flash("Quiz non trovato.", "danger")
        return redirect(url_for("quiz.quiz_list"))

    score = 0
    results = []
    for q in questions:
        answer = request.form.get(f"q_{q['index']}", "").upper()
        correct = q["correct"]
        is_correct = answer == correct
        if is_correct:
            score += 1
        results.append({
            "text": q["text"],
            "options": q["options"],
            "user_answer": answer,
            "correct": correct,
            "is_correct": is_correct,
        })

    title = filename.replace("_", " ").replace("-", " ").rsplit(".", 1)[0].title()
    quiz_result = QuizResult(
        user_id=current_user.id,
        quiz_filename=filename,
        quiz_title=title,
        score=score,
        total_questions=len(questions),
    )
    db.session.add(quiz_result)
    db.session.commit()

    return render_template(
        "quiz_result.html",
        filename=filename,
        title=title,
        results=results,
        score=score,
        total=len(questions),
        percentage=quiz_result.percentage,
    )


@quiz_bp.route("/history")
@login_required
def history():
    all_results = (
        QuizResult.query
        .filter_by(user_id=current_user.id)
        .order_by(QuizResult.completed_at.desc())
        .all()
    )
    return render_template("quiz_history.html", results=all_results)
