import re

import bcrypt
from flask import Blueprint, jsonify, request, session

from models import db, User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[a-zA-Z\s'-]+$")
PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$"
)


def _hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(plain, hashed):
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _user_dict(user):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def get_current_user():
    """Return the logged-in User or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    password = data.get("password", "")

    if not isinstance(email, str) or not EMAIL_RE.match(email):
        return jsonify({
            "error": "Please enter a valid email address (e.g. you@example.com)"
        }), 400

    if not isinstance(first_name, str) or not first_name or not NAME_RE.match(first_name):
        return jsonify({
            "error": "First name is required and must contain only letters"
        }), 400

    if len(first_name) > 100:
        return jsonify({"error": "First name must be 100 characters or fewer"}), 400

    if not isinstance(last_name, str) or not last_name or not NAME_RE.match(last_name):
        return jsonify({
            "error": "Last name is required and must contain only letters"
        }), 400

    if len(last_name) > 100:
        return jsonify({"error": "Last name must be 100 characters or fewer"}), 400

    if not isinstance(password, str) or not PASSWORD_RE.match(password):
        return jsonify({
            "error": "Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
        }), 400

    if User.query.filter(db.func.lower(User.email) == email.lower()).first():
        return jsonify({"error": "An account with this email already exists"}), 409

    user = User(
        email=email.lower(),
        first_name=first_name,
        last_name=last_name,
        hashed_password=_hash_password(password),
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"user": _user_dict(user)}), 201


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")

    user = User.query.filter(
        db.func.lower(User.email) == email.lower()
    ).first()

    if user is None or not _check_password(password, user.hashed_password):
        return jsonify({"error": "Invalid email or password"}), 401

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
