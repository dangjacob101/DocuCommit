from flask import Blueprint, jsonify, request

from models import db, Document, Branch, Commit
from routes.auth import get_current_user
from utils import compute_visual_diff, make_diff, reconstruct_branch_content

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


def get_required_int(data, keys):
    for key in keys:
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value, None
    return None, f"{keys[0]} is required and must be an integer"


def summarize_visual_diff(visual_diff):
    summary = {"added": 0, "removed": 0, "unchanged": 0, "modified": 0}
    for row in visual_diff:
        row_type = row["type"]
        if row_type == "equal":
            summary["unchanged"] += 1
        elif row_type == "insert":
            summary["added"] += 1
        elif row_type == "delete":
            summary["removed"] += 1
        elif row_type == "modify":
            summary["modified"] += 1
    return summary


def make_document_diff_payload(source_doc, target_doc):
    source = document_to_dict(source_doc)
    target = document_to_dict(target_doc)
    visual_diff = compute_visual_diff(source["content"], target["content"])

    return {
        "source_document": {
            "id": source["id"],
            "title": source["title"],
        },
        "target_document": {
            "id": target["id"],
            "title": target["title"],
        },
        "summary": summarize_visual_diff(visual_diff),
        "visual_diff": visual_diff,
        "unified_diff": make_diff(source["content"], target["content"]),
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

    doc = Document(title=title.strip(), owner_id=user.id)
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

    docs = Document.query.filter_by(owner_id=user.id).order_by(Document.id).all()
    return jsonify([document_to_dict(d) for d in docs])


@documents_bp.route("/documents/diff", methods=["POST"])
def diff_documents():
    data = request.get_json(silent=True) or {}
    source_document_id, source_error = get_required_int(
        data, ("source_document_id", "left_document_id", "document_id")
    )
    target_document_id, target_error = get_required_int(
        data, ("target_document_id", "right_document_id", "compare_document_id")
    )

    if source_error:
        return jsonify({"error": source_error}), 400
    if target_error:
        return jsonify({"error": target_error}), 400
    if source_document_id == target_document_id:
        return jsonify({"error": "document IDs must be different"}), 400

    docs = Document.query.filter(
        Document.id.in_([source_document_id, target_document_id])
    ).all()
    documents = {doc.id: doc for doc in docs}
    missing_ids = [
        doc_id
        for doc_id in (source_document_id, target_document_id)
        if doc_id not in documents
    ]

    if missing_ids:
        return (
            jsonify(
                {"error": "document not found", "missing_document_ids": missing_ids}
            ),
            404,
        )

    return jsonify(
        make_document_diff_payload(
            documents[source_document_id], documents[target_document_id]
        )
    )


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
