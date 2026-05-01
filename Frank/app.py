import os
import sqlite3
from difflib import unified_diff
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "documents.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                base_content TEXT NOT NULL DEFAULT '',
                current_content TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE (document_id, name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                delta TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO branches (
                document_id, name, base_content, current_content, created_at, updated_at
            )
            SELECT id, 'Main', content, content, created_at, updated_at
            FROM documents
            """
        )
        conn.commit()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def branch_to_dict(row):
    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "name": row["name"],
        "base_content": row["base_content"],
        "current_content": row["current_content"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def commit_to_dict(row):
    return {
        "id": row["id"],
        "branch_id": row["branch_id"],
        "message": row["message"],
        "delta": row["delta"],
        "created_at": row["created_at"],
    }


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def make_delta(previous_content, next_content):
    lines = unified_diff(
        previous_content.splitlines(),
        next_content.splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "\n".join(lines)


@app.route("/documents", methods=["POST"])
def create_document():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    content = data.get("content", "")
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required and must be a non-empty string"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content must be a string"}), 400
    now = now_iso()
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.execute(
            "INSERT INTO documents (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, content, now, now),
        )
        document_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO branches (
                document_id, name, base_content, current_content, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, "Main", content, content, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/documents", methods=["GET"])
def list_documents():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY id").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "document not found"}), 404
    return jsonify(row_to_dict(row))


@app.route("/documents/<int:doc_id>", methods=["PUT"])
def update_document(doc_id):
    data = request.get_json(silent=True) or {}
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "document not found"}), 404
        title = data.get("title", row["title"])
        content = data.get("content", row["content"])
        if not isinstance(title, str) or not title.strip():
            return jsonify({"error": "title must be a non-empty string"}), 400
        if not isinstance(content, str):
            return jsonify({"error": "content must be a string"}), 400
        conn.execute(
            "UPDATE documents SET title = ?, content = ?, updated_at = ? WHERE id = ?",
            (title, content, now_iso(), doc_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "document not found"}), 404
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    return "", 204


@app.route("/documents/<int:doc_id>/branches", methods=["POST"])
def create_branch(doc_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required and must be a non-empty string"}), 400

    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        document = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if document is None:
            return jsonify({"error": "document not found"}), 404

        source_branch_id = data.get("source_branch_id")
        if source_branch_id is None:
            content = document["content"]
        elif isinstance(source_branch_id, int):
            source_branch = conn.execute(
                "SELECT * FROM branches WHERE id = ? AND document_id = ?",
                (source_branch_id, doc_id),
            ).fetchone()
            if source_branch is None:
                return jsonify({"error": "source branch not found"}), 404
            content = source_branch["current_content"]
        else:
            return jsonify({"error": "source_branch_id must be an integer"}), 400

        now = now_iso()
        try:
            cur = conn.execute(
                """
                INSERT INTO branches (
                    document_id, name, base_content, current_content, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doc_id, name.strip(), content, content, now, now),
            )
        except sqlite3.IntegrityError:
            return jsonify({"error": "branch name already exists for this document"}), 409
        conn.commit()
        branch = conn.execute(
            "SELECT * FROM branches WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    return jsonify(branch_to_dict(branch)), 201


@app.route("/documents/<int:doc_id>/branches", methods=["GET"])
def list_branches(doc_id):
    with get_db() as conn:
        document = conn.execute(
            "SELECT id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if document is None:
            return jsonify({"error": "document not found"}), 404
        rows = conn.execute(
            "SELECT * FROM branches WHERE document_id = ? ORDER BY id", (doc_id,)
        ).fetchall()
    return jsonify([branch_to_dict(r) for r in rows])


@app.route("/branches/<int:branch_id>", methods=["GET"])
def get_branch(branch_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM branches WHERE id = ?", (branch_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "branch not found"}), 404
    return jsonify(branch_to_dict(row))


@app.route("/branches/<int:branch_id>/commits", methods=["POST"])
def create_branch_commit(branch_id):
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    content = data.get("content")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message is required and must be a non-empty string"}), 400
    if not isinstance(content, str):
        return jsonify({"error": "content is required and must be a string"}), 400

    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        branch = conn.execute(
            "SELECT * FROM branches WHERE id = ?", (branch_id,)
        ).fetchone()
        if branch is None:
            return jsonify({"error": "branch not found"}), 404
        if branch["status"] != "active":
            return jsonify({"error": "commits can only be added to active branches"}), 409
        if content == branch["current_content"]:
            return jsonify({"error": "content must differ from the current branch state"}), 400

        delta = make_delta(branch["current_content"], content)
        now = now_iso()
        cur = conn.execute(
            "INSERT INTO commits (branch_id, message, delta, created_at) VALUES (?, ?, ?, ?)",
            (branch_id, message.strip(), delta, now),
        )
        conn.execute(
            "UPDATE branches SET current_content = ?, updated_at = ? WHERE id = ?",
            (content, now, branch_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM commits WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    return jsonify(commit_to_dict(row)), 201


@app.route("/branches/<int:branch_id>/commits", methods=["GET"])
def list_branch_commits(branch_id):
    with get_db() as conn:
        branch = conn.execute(
            "SELECT id FROM branches WHERE id = ?", (branch_id,)
        ).fetchone()
        if branch is None:
            return jsonify({"error": "branch not found"}), 404
        rows = conn.execute(
            "SELECT * FROM commits WHERE branch_id = ? ORDER BY id", (branch_id,)
        ).fetchall()
    return jsonify([commit_to_dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
