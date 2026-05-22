import re

import bcrypt
from flask import Blueprint, jsonify, request, session

from models import db, User

auth_bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$"
)


def _hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(plain, hashed):
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _user_dict(user):
    return {"id": user.id, "username": user.username}


def get_current_user():
    """Return the logged-in User or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not USERNAME_RE.match(username):
        return jsonify({
            "error": "Username must be 3-50 characters and contain only letters, numbers, underscores, or hyphens"
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            "error": "Username must be between 3 and 50 characters"
        }), 400

    if not isinstance(password, str) or not PASSWORD_RE.match(password):
        return jsonify({
            "error": "Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
        }), 400

    if User.query.filter(db.func.lower(User.username) == username.lower()).first():
        return jsonify({"error": "Username is already taken"}), 409

    user = User(
        username=username.lower(),
        hashed_password=_hash_password(password),
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"user": _user_dict(user)}), 201


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter(
        db.func.lower(User.username) == username.lower()
    ).first()

    if user is None or not _check_password(password, user.hashed_password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user.id
    return jsonify({"user": _user_dict(user)})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return "", 204


@auth_bp.route("/auth/me", methods=["GET"])
def me():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({"user": _user_dict(user)})
