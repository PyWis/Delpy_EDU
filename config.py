import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///delpy_edu.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "noreply@delpyedu.it")
    BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Delpy EDU")
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

    QUIZ_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quiz")
