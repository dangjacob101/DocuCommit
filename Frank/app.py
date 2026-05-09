from flask import Flask
from flask_cors import CORS

from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    db.init_app(app)

    from routes.documents import documents_bp
    from routes.branches import branches_bp
    from routes.merge import merge_bp

    app.register_blueprint(documents_bp, url_prefix='/api')
    app.register_blueprint(branches_bp, url_prefix='/api')
    app.register_blueprint(merge_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
