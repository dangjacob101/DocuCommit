from flask import Blueprint, jsonify, request

from models import db, Document, Branch, Commit
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
        "content": content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


@documents_bp.route("/documents", methods=["POST"])
def create_document():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    content = data.get("content", "")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required and must be a non-empty string"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400

    doc = Document(title=title.strip(), owner_id=data.get("owner_id"))
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
    docs = Document.query.order_by(Document.id).all()
    return jsonify([document_to_dict(d) for d in docs])


@documents_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404
    return jsonify(document_to_dict(doc))


@documents_bp.route("/documents/<int:doc_id>", methods=["PUT"])
def update_document(doc_id):
    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404

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


@documents_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404
    db.session.delete(doc)
    db.session.commit()
    return "", 204
