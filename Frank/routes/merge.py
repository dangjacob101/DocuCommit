from flask import Blueprint, jsonify, request

from models import db, Branch, Commit, Document
from routes.auth import get_current_user
from utils import reconstruct_branch_content, reconstruct_content, make_diff
from merge_engine import (
    three_way_merge,
    apply_resolutions,
    validate_linear_progression,
    merge_summary,
)

merge_bp = Blueprint("merge", __name__)


def _get_base_text(branch, main_branch):
    """Reconstruct the common-ancestor text at the branch point."""
    if branch.branched_from_commit_id is not None:
        base_commits = Commit.query.filter(
            Commit.branch_id == main_branch.id,
            Commit.id <= branch.branched_from_commit_id,
        ).order_by(Commit.id).all()
    else:
        base_commits = []
    return reconstruct_content(base_commits)


def _overwrite_main_with_branch(main_branch, branch):
    main_content = reconstruct_branch_content(main_branch)
    branch_content = reconstruct_branch_content(branch)

    merge_commit = None
    if main_content != branch_content:
        merge_commit = Commit(
            branch_id=main_branch.id,
            message=f"Merge branch '{branch.name}' into Main",
            diff_patch=make_diff(main_content, branch_content),
        )
        db.session.add(merge_commit)

    db.session.delete(branch)
    return branch_content, merge_commit


@merge_bp.route("/branches/<int:branch_id>/merge/preview", methods=["GET"])
def merge_preview(branch_id):
    """Return a three-way merge preview with conflict hunks and summary stats."""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404

    doc = Document.query.get(branch.document_id)
    if doc is None or doc.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    if branch.is_main:
        return jsonify({"error": "cannot merge the Main branch into itself"}), 400
    if branch.status != "active":
        return jsonify({"error": "branch has already been merged"}), 409

    main_branch = Branch.query.filter_by(
        document_id=branch.document_id, is_main=True
    ).first()
    if main_branch is None:
        return jsonify({"error": "main branch not found"}), 500

    base_text = _get_base_text(branch, main_branch)
    main_text = reconstruct_branch_content(main_branch)
    branch_text = reconstruct_branch_content(branch)

    hunks = three_way_merge(base_text, main_text, branch_text)
    has_conflicts = any(h["kind"] == "conflict" for h in hunks)
    summary = merge_summary(base_text, main_text, branch_text)
    progression = validate_linear_progression(base_text, main_text, branch_text)

    return jsonify({
        "branch_id": branch.id,
        "branch_name": branch.name,
        "main_name": main_branch.name,
        "has_conflicts": has_conflicts,
        "hunks": hunks,
        "summary": summary,
        "progression": progression,
    })


@merge_bp.route("/branches/<int:branch_id>/merge", methods=["POST"])
def merge_branch(branch_id):
    user = get_current_user()
    if user is None:
        return jsonify({"error": "authentication required"}), 401

    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404

    doc = Document.query.get(branch.document_id)
    if doc is None or doc.owner_id != user.id:
        return jsonify({"error": "access denied"}), 403

    if branch.is_main:
        return jsonify({"error": "cannot merge the Main branch into itself"}), 400
    if branch.status != "active":
        return jsonify({"error": "only active branches can be merged"}), 409

    main_branch = Branch.query.filter_by(
        document_id=branch.document_id, is_main=True
    ).first()
    if main_branch is None:
        return jsonify({"error": "main branch not found"}), 500

    branch_has_commits = Commit.query.filter_by(branch_id=branch.id).first() is not None
    if not branch_has_commits:
        base_text = _get_base_text(branch, main_branch)
        branch_text = reconstruct_branch_content(branch)
        if base_text == branch_text:
            return jsonify({"error": "branch has no changes to merge"}), 400

    base_text = _get_base_text(branch, main_branch)
    main_text = reconstruct_branch_content(main_branch)
    branch_text = reconstruct_branch_content(branch)

    progression = validate_linear_progression(base_text, main_text, branch_text)
    data = request.get_json(silent=True) or {}
    resolutions = data.get("resolutions")

    if progression["is_linear"]:
        branch_id = branch.id
        branch_name = branch.name
        main_content, merge_commit = _overwrite_main_with_branch(main_branch, branch)
        db.session.commit()
        return jsonify({
            "message": f"Branch '{branch_name}' merged into Main",
            "branch_id": branch_id,
            "branch_status": "deleted",
            "main_branch_id": main_branch.id,
            "merge_commit_id": merge_commit.id if merge_commit else None,
            "main_content": main_content,
        })

    if resolutions is None:
        if progression["has_conflicts"]:
            return jsonify({
                "error": "Main has diverged since this branch was created. "
                         "Conflict resolution required.",
                "conflict": True,
                "branch_id": branch.id,
            }), 409
        resolutions = {}

    hunks = three_way_merge(base_text, main_text, branch_text)

    conflict_ids = {h["id"] for h in hunks if h["kind"] == "conflict"}
    missing = conflict_ids - set(resolutions.keys())
    if missing:
        return jsonify({
            "error": f"Missing resolutions for conflicts: {sorted(missing)}",
            "missing_ids": sorted(missing),
        }), 400

    try:
        merged_text = apply_resolutions(hunks, resolutions)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    branch_id = branch.id
    branch_name = branch.name

    merge_commit = None
    if main_text != merged_text:
        merge_commit = Commit(
            branch_id=main_branch.id,
            message=f"Merge branch '{branch_name}' into Main (conflicts resolved)",
            diff_patch=make_diff(main_text, merged_text),
        )
        db.session.add(merge_commit)

    db.session.delete(branch)
    db.session.commit()

    return jsonify({
        "message": f"Branch '{branch_name}' merged into Main (conflicts resolved)",
        "branch_id": branch_id,
        "branch_status": "deleted",
        "main_branch_id": main_branch.id,
        "merge_commit_id": merge_commit.id if merge_commit else None,
        "main_content": merged_text,
    })
