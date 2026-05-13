import csv
import os
from flask import current_app


def get_quiz_list():
    folder = current_app.config["QUIZ_FOLDER"]
    quizzes = []
    if not os.path.isdir(folder):
        return quizzes
    for filename in sorted(os.listdir(folder)):
        if filename.endswith(".csv"):
            title = filename.replace("_", " ").replace("-", " ").rsplit(".", 1)[0].title()
            quizzes.append({"filename": filename, "title": title})
    return quizzes


def load_quiz(filename):
    folder = current_app.config["QUIZ_FOLDER"]
    filepath = os.path.join(folder, filename)

    if not os.path.isfile(filepath):
        return None

    # Prevent path traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(folder)):
        return None

    questions = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            options = []
            for key in ["A", "B", "C", "D"]:
                col = f"opzione_{key}" if f"opzione_{key}" in row else key
                if col in row and row[col].strip():
                    options.append({"key": key, "text": row[col].strip()})

            correct_raw = row.get("risposta_corretta", row.get("correct", "")).strip().upper()

            questions.append({
                "index": i,
                "text": row.get("domanda", row.get("question", "")).strip(),
                "options": options,
                "correct": correct_raw,
            })
    return questions
