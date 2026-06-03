from flask import Blueprint, jsonify, request

from models import db, Project, Document
from routes.auth import get_current_user

projects_bp = Blueprint("projects", __name__)


def project_to_dict(project, include_documents=False):
    data = {
        "id": project.id,
        "name": project.name,
        "owner_id": project.owner_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }
    if include_documents:
        data["documents"] = [
            {"id": d.id, "title": d.title}
            for d in sorted(project.documents, key=lambda x: x.id)
        ]
    return data


@projects_bp.route("/projects", methods=["POST"])
def create_project():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required and must be a non-empty string"}), 400

    project = Project(name=name.strip(), owner_id=user.id)
    db.session.add(project)
    db.session.commit()
    return jsonify(project_to_dict(project)), 201


@projects_bp.route("/projects", methods=["GET"])
def list_projects():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    projects = (
        Project.query.filter_by(owner_id=user.id).order_by(Project.id).all()
    )
    return jsonify([project_to_dict(p) for p in projects])


@projects_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if project.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    return jsonify(project_to_dict(project, include_documents=True))


@projects_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if project.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    db.session.delete(project)
    db.session.commit()
    return "", 204


@projects_bp.route("/projects/<int:project_id>", methods=["PATCH"])
def rename_project(project_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if project.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name must be a non-empty string"}), 400

    project.name = name.strip()
    db.session.commit()
    return jsonify(project_to_dict(project))
