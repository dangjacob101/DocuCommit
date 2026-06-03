import bcrypt
from flask import Flask
from flask_cors import CORS

from config import Config
from models import (
    db,
    User,
    Document,
    Project,
    create_missing_indexes,
    migrate_users_schema,
    migrate_documents_project_id,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

    db.init_app(app)

    from routes.documents import documents_bp
    from routes.branches import branches_bp
    from routes.merge import merge_bp
    from routes.auth import auth_bp, init_oauth
    from routes.projects import projects_bp

    app.register_blueprint(documents_bp, url_prefix='/api')
    app.register_blueprint(branches_bp, url_prefix='/api')
    app.register_blueprint(merge_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(projects_bp, url_prefix='/api')

    init_oauth(app)

    with app.app_context():
        migrate_users_schema()
        db.create_all()
        create_missing_indexes()
        _seed_default_user()
        migrate_documents_project_id()

    return app


def _seed_default_user():
    existing = User.query.filter(
        db.func.lower(User.email) == "frank@docucommit.com"
    ).first()

    if existing is None:
        hashed = bcrypt.hashpw(
            "CS35LTeamprofile!".encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        existing = User(
            email="frank@docucommit.com",
            first_name="Frank",
            last_name="Admin",
            hashed_password=hashed,
        )
        db.session.add(existing)
        db.session.flush()

    default_proj = Project.query.filter_by(owner_id=existing.id).order_by(Project.id).first()
    if default_proj is None:
        default_proj = Project(name="Frank's Workspace", owner_id=existing.id)
        db.session.add(default_proj)
        db.session.flush()

    Document.query.filter(Document.owner_id.is_(None)).update(
        {"owner_id": existing.id, "project_id": default_proj.id}
    )
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
