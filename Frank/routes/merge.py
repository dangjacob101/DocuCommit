from flask import Blueprint, jsonify

from models import db, Branch, Commit
from utils import reconstruct_branch_content, make_diff

merge_bp = Blueprint("merge", __name__)


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
    if branch.branched_from_commit_id is not None:
        newer_on_main = Commit.query.filter(
            Commit.branch_id == main_branch.id,
            Commit.id > branch.branched_from_commit_id,
        ).first()
        if newer_on_main is not None:
            return jsonify({
                "error": "Main has diverged since this branch was created. "
                         "Clean merge not possible (conflict resolution required)."
            }), 409

    # Perform the merge: replay branch commits onto Main
    main_content = reconstruct_branch_content(main_branch)
    branch_content = reconstruct_branch_content(branch)

    if main_content != branch_content:
        diff_patch = make_diff(main_content, branch_content)
        merge_commit = Commit(
            branch_id=main_branch.id,
            message=f"Merge branch '{branch.name}' into Main",
            diff_patch=diff_patch,
        )
        db.session.add(merge_commit)

    branch.status = "merged"
    db.session.commit()

    return jsonify({
        "message": f"Branch '{branch.name}' merged into Main",
        "branch_id": branch.id,
        "branch_status": branch.status,
        "main_content": reconstruct_branch_content(main_branch),
    })
