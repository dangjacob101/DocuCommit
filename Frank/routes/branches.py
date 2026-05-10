from flask import Blueprint, jsonify, request

from models import db, Document, Branch, Commit
from utils import compute_visual_diff, make_diff, reconstruct_branch_content, extract_plain_text

branches_bp = Blueprint("branches", __name__)


def branch_to_dict(branch):
    return {
        "id": branch.id,
        "document_id": branch.document_id,
        "name": branch.name,
        "is_main": branch.is_main,
        "branched_from_commit_id": branch.branched_from_commit_id,
        "status": branch.status,
        "current_content": reconstruct_branch_content(branch),
        "created_at": branch.created_at.isoformat() if branch.created_at else None,
    }


def commit_to_dict(commit):
    return {
        "id": commit.id,
        "branch_id": commit.branch_id,
        "message": commit.message,
        "diff_patch": commit.diff_patch,
        "created_at": commit.created_at.isoformat() if commit.created_at else None,
    }


@branches_bp.route("/documents/<int:doc_id>/branches", methods=["POST"])
def create_branch(doc_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required and must be a non-empty string"}), 400

    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404

    existing = Branch.query.filter_by(document_id=doc_id, name=name.strip()).first()
    if existing:
        return jsonify({"error": "branch name already exists for this document"}), 409

    # Determine which branch to fork from
    source_branch_id = data.get("source_branch_id")
    if source_branch_id is not None:
        source_branch = Branch.query.filter_by(
            id=source_branch_id, document_id=doc_id
        ).first()
        if source_branch is None:
            return jsonify({"error": "source branch not found"}), 404
    else:
        source_branch = Branch.query.filter_by(
            document_id=doc_id, is_main=True
        ).first()

    # Capture the latest commit on the source branch as the snapshot point
    branched_from_commit_id = None
    if source_branch and source_branch.commits:
        branched_from_commit_id = source_branch.commits[-1].id

    new_branch = Branch(
        document_id=doc_id,
        name=name.strip(),
        is_main=False,
        branched_from_commit_id=branched_from_commit_id,
        status="active",
    )
    db.session.add(new_branch)
    db.session.commit()

    return jsonify(branch_to_dict(new_branch)), 201


@branches_bp.route("/documents/<int:doc_id>/branches", methods=["GET"])
def list_branches(doc_id):
    doc = Document.query.get(doc_id)
    if doc is None:
        return jsonify({"error": "document not found"}), 404

    branches = Branch.query.filter_by(document_id=doc_id).order_by(Branch.id).all()
    return jsonify([branch_to_dict(b) for b in branches])


@branches_bp.route("/branches/<int:branch_id>", methods=["GET"])
def get_branch(branch_id):
    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404
    return jsonify(branch_to_dict(branch))


@branches_bp.route("/branches/<int:branch_id>/commits", methods=["POST"])
def create_commit(branch_id):
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    content = data.get("content")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message is required and must be a non-empty string"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content is required and must be a string"}), 400

    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404
    if branch.status != "active":
        return jsonify({"error": "commits can only be added to active branches"}), 409

    current_content = reconstruct_branch_content(branch)
    if content == current_content:
        return jsonify({"error": "content must differ from the current branch state"}), 400

    diff_patch = make_diff(current_content, content)
    commit = Commit(
        branch_id=branch_id,
        message=message.strip(),
        diff_patch=diff_patch,
    )
    db.session.add(commit)
    db.session.commit()

    return jsonify(commit_to_dict(commit)), 201


@branches_bp.route("/branches/<int:branch_id>/commits", methods=["GET"])
def list_commits(branch_id):
    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404

    commits = Commit.query.filter_by(branch_id=branch_id).order_by(Commit.id).all()
    return jsonify([commit_to_dict(c) for c in commits])


@branches_bp.route("/branches/<int:branch_id>/diff", methods=["GET"])
def diff_branch_vs_main(branch_id):
    """Compare a branch against its document's Main branch.

    Returns the same visual_diff payload shape as POST /documents/diff so the
    frontend can use a single DiffViewer component for both surfaces.

    Query params:
        w=1  Ignore whitespace differences (like GitHub's ?w=1).
    """
    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404

    main_branch = Branch.query.filter_by(
        document_id=branch.document_id, is_main=True
    ).first()
    if main_branch is None:
        return jsonify({"error": "main branch not found"}), 500

    main_raw = reconstruct_branch_content(main_branch)
    branch_raw = reconstruct_branch_content(branch)

    # Diff on readable prose, not raw JSON / HTML
    main_text = extract_plain_text(main_raw)
    branch_text = extract_plain_text(branch_raw)

    visual_diff = compute_visual_diff(main_text, branch_text)

    # GitHub-style: ?w=1 reclassifies whitespace-only changes as "equal"
    ignore_ws = request.args.get("w") == "1"
    if ignore_ws:
        import re
        def _strip_ws(s):
            return re.sub(r"\s+", "", s)

        for row in visual_diff:
            if row["type"] == "modify":
                old_stripped = _strip_ws(row.get("old", ""))
                new_stripped = _strip_ws(row.get("new", ""))
                if old_stripped == new_stripped:
                    # Whitespace-only change — reclassify as equal
                    row["type"] = "equal"
                    row["content"] = row["new"]
                    row.pop("old", None)
                    row.pop("new", None)
                    row.pop("words", None)

    summary = {"added": 0, "removed": 0, "unchanged": 0, "modified": 0}
    for row in visual_diff:
        t = row["type"]
        if t == "equal":
            summary["unchanged"] += 1
        elif t == "insert":
            summary["added"] += 1
        elif t == "delete":
            summary["removed"] += 1
        elif t == "modify":
            summary["modified"] += 1

    return jsonify({
        "branch": {"id": branch.id, "name": branch.name},
        "main": {"id": main_branch.id, "name": main_branch.name},
        "ignore_whitespace": ignore_ws,
        "summary": summary,
        "visual_diff": visual_diff,
    })
