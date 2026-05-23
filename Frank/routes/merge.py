from flask import Blueprint, jsonify

from models import db, Branch, Commit
from utils import reconstruct_branch_content, make_diff

merge_bp = Blueprint("merge", __name__)


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

    # Clean merge check: Main must have no new commits after branched_from_commit_id
    if _main_has_new_commits(main_branch, branch.branched_from_commit_id):
        return jsonify({
            "error": "Main has diverged since this branch was created. "
                     "Clean merge not possible (conflict resolution required)."
        }), 409

    # Archive the branch and update Main by storing the overwrite as a Main commit.
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
