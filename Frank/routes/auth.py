import os
import re
import uuid

import bcrypt
import requests as http_requests
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, jsonify, redirect, request, session, send_from_directory, current_app
from werkzeug.utils import secure_filename

from models import db, User

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()


def init_oauth(app):
    """Register the Google OAuth client. Call this once from app.py."""
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[a-zA-Z\s'-]+$")
PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$"
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
        "profile_picture_url": f"/api/auth/profile-picture/{user.id}" if user.profile_picture else None,
    }


def get_current_user():
    """Return the logged-in User or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def _uploads_dir():
    """Return (and lazily create) the profile-pictures upload directory."""
    path = os.path.join(current_app.instance_path, "uploads", "profile_pictures")
    os.makedirs(path, exist_ok=True)
    return path


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


@auth_bp.route("/auth/profile-picture", methods=["POST"])
def upload_profile_picture():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "not authenticated"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PNG, JPG, GIF, or WebP"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"error": "File too large. Maximum size is 5 MB"}), 400

    # Delete old profile picture if it exists
    if user.profile_picture:
        old_path = os.path.join(_uploads_dir(), user.profile_picture)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save with a unique filename
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    file.save(os.path.join(_uploads_dir(), filename))

    user.profile_picture = filename
    db.session.commit()

    return jsonify({"user": _user_dict(user)})


@auth_bp.route("/auth/profile-picture/<int:user_id>", methods=["GET"])
def serve_profile_picture(user_id):
    target_user = User.query.get(user_id)
    if target_user is None or not target_user.profile_picture:
        return jsonify({"error": "No profile picture found"}), 404

    return send_from_directory(_uploads_dir(), target_user.profile_picture)


@auth_bp.route("/auth/google/login", methods=["GET"])
def google_login():
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = current_app.config.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/google/callback"
    )
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback", methods=["GET"])
def google_callback():
    """Handle the OAuth callback from Google.

    - Exchange the authorization code for tokens.
    - Fetch the user's profile from Google.
    - Find an existing user by google_id or email; create one if needed.
    - Set the session and redirect back to the React frontend.
    """
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        return redirect("http://localhost:5173/?error=oauth_failed")

    userinfo = token.get("userinfo") or {}
    google_id = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower()
    first_name = userinfo.get("given_name", "")
    last_name = userinfo.get("family_name", "")

    if not google_id or not email:
        return redirect("http://localhost:5173/?error=oauth_missing_info")

    # 1. Try to find by Google ID first (returning user who logged in via Google before)
    user = User.query.filter_by(google_id=google_id).first()

    if user is None:
        # 2. Try to find by email (existing account created with email/password)
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user is not None:
            # Link Google ID to the existing account
            user.google_id = google_id
        else:
            # 3. Brand-new user — create an account
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
                # hashed_password is None — OAuth-only users don't have a password
            )
            db.session.add(user)

    db.session.commit()
    session["user_id"] = user.id
    return redirect("http://localhost:5173/")
