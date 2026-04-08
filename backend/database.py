# database.py
# Initializes the SQLAlchemy database instance

from flask_sqlalchemy import SQLAlchemy  # type: ignore

# This db object is shared across all files
db = SQLAlchemy()


def init_db(app):
    """Connect database to Flask app and create all tables"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("[Database] SQLite connected [OK]")
        print("[Database] Tables created [OK]")
