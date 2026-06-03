from flask import Blueprint, jsonify, request, send_file

from docx_generator import generate_docx_from_content
from models import db, Document, Branch, Commit, Project
from routes.auth import get_current_user
from utils import make_diff, reconstruct_branch_content

documents_bp = Blueprint("documents", __name__)


def document_to_dict(doc):
    main_branch = Branch.query.filter_by(document_id=doc.id, is_main=True).first()
    content = ""
    updated_at = doc.created_at
    if main_branch:
        content = reconstruct_branch_content(main_branch)
        latest_commit = Commit.query.filter_by(branch_id=main_branch.id).order_by(
            Commit.id.desc()
        ).first()
        if latest_commit and latest_commit.created_at:
            updated_at = latest_commit.created_at
    return {
        "id": doc.id,
        "title": doc.title,
        "owner_id": doc.owner_id,
        "project_id": doc.project_id,
        "content": content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def document_commit_to_dict(
    commit_id, branch_id, branch_name, is_main, message, diff_patch, created_at
):
    return {
        "id": commit_id,
        "branch_id": branch_id,
        "branch_name": branch_name,
        "branch_is_main": is_main,
        "message": message,
        "diff_patch": diff_patch,
        "created_at": created_at.isoformat() if created_at else None,
    }


@documents_bp.route("/documents", methods=["POST"])
def create_document():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    content = data.get("content", "")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required and must be a non-empty string"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400

    project_id = data.get("project_id")
    if project_id is not None:
        project = Project.query.get(project_id)
        if project is None:
            return jsonify({"error": "project not found"}), 404
        if project.owner_id != user.id:
            return jsonify({"error": "access denied"}), 403
    else:
        project = (
            Project.query.filter_by(owner_id=user.id).order_by(Project.id).first()
        )
        if project is None:
            workspace_name = (
                f"{user.first_name}'s Workspace" if user.first_name else "My Workspace"
            )
            project = Project(name=workspace_name, owner_id=user.id)
            db.session.add(project)
            db.session.flush()
        project_id = project.id

    doc = Document(title=title.strip(), owner_id=user.id, project_id=project_id)
    db.session.add(doc)
    db.session.flush()

    main_branch = Branch(
        document_id=doc.id,
        name="Main",
        is_main=True,
        status="active",
    )
    db.session.add(main_branch)
    db.session.flush()

    if content:
        diff_patch = make_diff("", content)
        initial_commit = Commit(
            branch_id=main_branch.id,
            message="Initial content",
            diff_patch=diff_patch,
        )
        db.session.add(initial_commit)

    db.session.commit()
    return jsonify(document_to_dict(doc)), 201


@documents_bp.route("/documents", methods=["GET"])
def list_documents():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    query = Document.query.filter_by(owner_id=user.id)

    search = request.args.get("q", "").strip()
    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))

    docs = query.order_by(Document.id).all()
    return jsonify([document_to_dict(d) for d in docs])


@documents_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404
    if doc.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403
    return jsonify(document_to_dict(doc))


@documents_bp.route("/documents/<int:doc_id>/commits", methods=["GET"])
def list_document_commits(doc_id):
    doc_exists = (
        Document.query.with_entities(Document.id)
        .filter(Document.id == doc_id)
        .first()
    )
    if doc_exists is None:
        return jsonify({"error": "document not found"}), 404

    rows = (
        db.session.query(
            Commit.id,
            Commit.branch_id,
            Branch.name,
            Branch.is_main,
            Commit.message,
            Commit.diff_patch,
            Commit.created_at,
        )
        .join(Branch, Commit.branch_id == Branch.id)
        .filter(Branch.document_id == doc_id)
        .order_by(Commit.id)
        .all()
    )

    return jsonify([document_commit_to_dict(*row) for row in rows])


@documents_bp.route("/documents/<int:doc_id>", methods=["PUT"])
def update_document(doc_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404
    if doc.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    data = request.get_json(silent=True) or {}
    title = data.get("title", doc.title)

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title must be a non-empty string"}), 400

    doc.title = title.strip()

    # If content is provided, commit it to the Main branch
    content = data.get("content")
    if content is not None:
        if not isinstance(content, str):
            return jsonify({"error": "content must be a string"}), 400
        main_branch = Branch.query.filter_by(document_id=doc.id, is_main=True).first()
        if main_branch:
            current = reconstruct_branch_content(main_branch)
            if content != current:
                diff_patch = make_diff(current, content)
                commit = Commit(
                    branch_id=main_branch.id,
                    message="Updated document",
                    diff_patch=diff_patch,
                )
                db.session.add(commit)

    db.session.commit()
    return jsonify(document_to_dict(doc))


@documents_bp.route("/documents/<int:doc_id>/export", methods=["GET"])
def export_document(doc_id):
    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404

    main_branch = Branch.query.filter_by(document_id=doc.id, is_main=True).first()
    if main_branch is None:
        return jsonify({"error": "main branch not found"}), 500

    raw = reconstruct_branch_content(main_branch)
    stream = generate_docx_from_content(doc.title, raw)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"{doc.title}.docx",
    )


@documents_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404
    if doc.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403
    db.session.delete(doc)
    db.session.commit()
    return "", 204
