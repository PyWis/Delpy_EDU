import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()


def _migrate_school_id_nullable(db_file):
    """Recreate users table with nullable school_id if the column is currently NOT NULL."""
    import sqlite3
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = cur.fetchall()
        # Each row: (cid, name, type, notnull, dflt_value, pk)
        school_id_col = next((c for c in cols if c[1] == "school_id"), None)
        if school_id_col and school_id_col[3] == 1:  # notnull == 1
            cur.execute("PRAGMA foreign_keys=off")
            cur.execute("""
                CREATE TABLE users_v2 (
                    id INTEGER NOT NULL PRIMARY KEY,
                    school_id INTEGER REFERENCES schools(id),
                    username VARCHAR(80) NOT NULL,
                    email VARCHAR(150) NOT NULL UNIQUE,
                    password_hash VARCHAR(256) NOT NULL,
                    role VARCHAR(20),
                    is_active BOOLEAN,
                    created_at DATETIME
                )
            """)
            cur.execute("INSERT INTO users_v2 SELECT * FROM users")
            cur.execute("DROP TABLE users")
            cur.execute("ALTER TABLE users_v2 RENAME TO users")
            conn.commit()
            cur.execute("PRAGMA foreign_keys=on")
            conn.commit()
            return True
        return False
    finally:
        conn.close()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Accedi per continuare."
    login_manager.login_message_category = "warning"

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.quiz import quiz_bp
    from routes.superadmin import superadmin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(quiz_bp, url_prefix="/quiz")
    app.register_blueprint(superadmin_bp, url_prefix="/superadmin")

    with app.app_context():
        db.create_all()

    @app.cli.command("create-superadmin")
    @click.option("--email", prompt="Email superadmin", help="Email dell'utente superadmin")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Password (minimo 8 caratteri)",
    )
    @click.option("--username", prompt="Nome utente", default="Superadmin", show_default=True)
    def create_superadmin_cmd(email, password, username):
        """Crea un utente superadmin per gestire scuole e utenti da CLI."""
        from models import User

        email = email.strip().lower()
        username = username.strip()

        if len(password) < 8:
            click.echo("Errore: la password deve essere di almeno 8 caratteri.", err=True)
            return

        db_url = app.config["SQLALCHEMY_DATABASE_URI"]
        if db_url.startswith("sqlite:///"):
            db_file = db_url[len("sqlite:///"):]
            if not os.path.isabs(db_file):
                db_file = os.path.join(app.root_path, db_file)
            if os.path.exists(db_file):
                migrated = _migrate_school_id_nullable(db_file)
                if migrated:
                    click.echo("Schema aggiornato: school_id ora opzionale.")

        if User.query.filter_by(email=email).first():
            click.echo(f"Utente con email '{email}' già esistente. Nessuna modifica.")
            return

        user = User(school_id=None, username=username, email=email, role="superadmin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Superadmin '{username}' creato con successo (email: {email}).")

    return app


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
