import bcrypt
from flask import Flask
from flask_cors import CORS

from config import Config
from models import db, User, Document, create_missing_indexes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

    db.init_app(app)

    from routes.documents import documents_bp
    from routes.branches import branches_bp
    from routes.merge import merge_bp
    from routes.auth import auth_bp

    app.register_blueprint(documents_bp, url_prefix='/api')
    app.register_blueprint(branches_bp, url_prefix='/api')
    app.register_blueprint(merge_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()
        create_missing_indexes()
        _seed_default_user()

    return app


def _seed_default_user():
    """Create the default 'frank' user if it does not exist and assign
    any orphaned documents (owner_id IS NULL) to that user."""
    existing = User.query.filter(
        db.func.lower(User.username) == "frank"
    ).first()

    if existing is None:
        hashed = bcrypt.hashpw(
            "CS35LTeamprofile!".encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        existing = User(username="frank", hashed_password=hashed)
        db.session.add(existing)
        db.session.flush()

    # Reassign orphaned documents to the default user
    Document.query.filter(Document.owner_id.is_(None)).update(
        {"owner_id": existing.id}
    )
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
