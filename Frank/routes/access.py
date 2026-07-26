from flask import jsonify

from models import db, Branch, Document
from routes.auth import get_current_user


def require_owned_document(document_id):
    """Return an owned document or a Flask authentication/authorization error."""
    user = get_current_user()
    if user is None:
        return None, (jsonify({"error": "authentication required"}), 401)

    document = db.session.get(Document, document_id)
    if document is None:
        return None, (jsonify({"error": "document not found"}), 404)
    if document.owner_id != user.id:
        return None, (jsonify({"error": "access denied"}), 403)

    return document, None


def require_owned_branch(branch_id):
    """Return a branch owned through its document or an access-control error."""
    user = get_current_user()
    if user is None:
        return None, (jsonify({"error": "authentication required"}), 401)

    branch = db.session.get(Branch, branch_id)
    if branch is None:
        return None, (jsonify({"error": "branch not found"}), 404)
    if branch.document is None or branch.document.owner_id != user.id:
        return None, (jsonify({"error": "access denied"}), 403)

    return branch, None
