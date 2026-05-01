import os
import sqlite3
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
        conn.commit()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def now_iso():
    return datetime.now(timezone.utc).isoformat()


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
        cur = conn.execute(
            "INSERT INTO documents (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, content, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (cur.lastrowid,)
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
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "document not found"}), 404
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
