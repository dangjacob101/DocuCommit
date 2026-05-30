from flask import Blueprint, jsonify, request

from models import db, Branch, Commit
from utils import reconstruct_branch_content, reconstruct_content, make_diff
from merge_engine import three_way_merge, apply_resolutions

merge_bp = Blueprint("merge", __name__)


def _get_base_text(branch, main_branch):
    """Reconstruct the common-ancestor text (the snapshot at branch point)."""
    if branch.branched_from_commit_id is not None:
        base_commits = Commit.query.filter(
            Commit.branch_id == main_branch.id,
            Commit.id <= branch.branched_from_commit_id,
        ).order_by(Commit.id).all()
    else:
        base_commits = []
    return reconstruct_content(base_commits)


def _main_has_new_commits(main_branch, branched_from_commit_id):
    query = Commit.query.filter(Commit.branch_id == main_branch.id)
    if branched_from_commit_id is not None:
        query = query.filter(Commit.id > branched_from_commit_id)
    return query.first() is not None


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

    branch.status = "merged"
    return branch_content, merge_commit


# ── Merge preview ──────────────────────────────────────────────────

@merge_bp.route("/branches/<int:branch_id>/merge/preview", methods=["GET"])
def merge_preview(branch_id):
    """Return a three-way merge preview with conflict hunks.

    The frontend uses this to populate the ConflictResolver UI.
    """
    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404
    if branch.is_main:
        return jsonify({"error": "cannot merge the Main branch into itself"}), 400

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

    return jsonify({
        "branch_id": branch.id,
        "branch_name": branch.name,
        "main_name": main_branch.name,
        "has_conflicts": has_conflicts,
        "hunks": hunks,
    })


# ── Merge execution ───────────────────────────────────────────────

@merge_bp.route("/branches/<int:branch_id>/merge", methods=["POST"])
def merge_branch(branch_id):
    branch = Branch.query.get(branch_id)
    if branch is None:
        return jsonify({"error": "branch not found"}), 404
    if branch.is_main:
        return jsonify({"error": "cannot merge the Main branch into itself"}), 400
    if branch.status != "active":
        return jsonify({"error": "only active branches can be merged"}), 409

    main_branch = Branch.query.filter_by(
        document_id=branch.document_id, is_main=True
    ).first()
    if main_branch is None:
        return jsonify({"error": "main branch not found"}), 500

    diverged = _main_has_new_commits(main_branch, branch.branched_from_commit_id)
    data = request.get_json(silent=True) or {}
    resolutions = data.get("resolutions")

    # ── Fast-forward (clean) merge ─────────────────────────────────
    if not diverged:
        main_content, merge_commit = _overwrite_main_with_branch(main_branch, branch)
        db.session.commit()
        return jsonify({
            "message": f"Branch '{branch.name}' merged into Main",
            "branch_id": branch.id,
            "branch_status": branch.status,
            "main_branch_id": main_branch.id,
            "merge_commit_id": merge_commit.id if merge_commit else None,
            "main_content": main_content,
        })

    # ── Diverged: conflict merge ───────────────────────────────────
    if resolutions is None:
        # No resolutions provided — tell the frontend to show ConflictResolver
        return jsonify({
            "error": "Main has diverged since this branch was created. "
                     "Conflict resolution required.",
            "conflict": True,
            "branch_id": branch.id,
        }), 409

    # Resolutions provided — perform three-way merge
    base_text = _get_base_text(branch, main_branch)
    main_text = reconstruct_branch_content(main_branch)
    branch_text = reconstruct_branch_content(branch)

    hunks = three_way_merge(base_text, main_text, branch_text)

    # Validate all conflict hunks have resolutions
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

    # Create the merge commit on Main
    current_main_text = main_text
    merge_commit = None
    if current_main_text != merged_text:
        merge_commit = Commit(
            branch_id=main_branch.id,
            message=f"Merge branch '{branch.name}' into Main (conflicts resolved)",
            diff_patch=make_diff(current_main_text, merged_text),
        )
        db.session.add(merge_commit)

    branch.status = "merged"
    db.session.commit()

    return jsonify({
        "message": f"Branch '{branch.name}' merged into Main (conflicts resolved)",
        "branch_id": branch.id,
        "branch_status": branch.status,
        "main_branch_id": main_branch.id,
        "merge_commit_id": merge_commit.id if merge_commit else None,
        "main_content": merged_text,
    })
