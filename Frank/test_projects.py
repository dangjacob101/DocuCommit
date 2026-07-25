# tests for the project CRUD endpoints. uses a throwaway sqlite db so the
# real documents.db is never touched.

import os
import sys
import tempfile
import warnings

_test_dir = tempfile.mkdtemp(prefix="docucommit_projects_")
TEST_DB_PATH = os.path.join(_test_dir, "projects.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

warnings.filterwarnings("ignore", message=r"Can't sort tables for DROP")

sys.path.insert(0, ".")

from app import app  # noqa: E402
from models import db  # noqa: E402
from testing_helpers import register_test_user  # noqa: E402


def fresh_client():
    """Wipe the test database and return an authenticated client."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    client = app.test_client()
    register_test_user(client)
    return client


def register_and_login(client, email, first_name="Test", last_name="User"):
    register_test_user(
        client,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )


def test_create_project():
    client = fresh_client()
    r = client.post("/api/projects", json={"name": "Acme Engagement"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["name"] == "Acme Engagement"
    assert isinstance(data["id"], int)
    print("PASS: create project")


def test_create_project_requires_name():
    client = fresh_client()
    r = client.post("/api/projects", json={})
    assert r.status_code == 400
    r = client.post("/api/projects", json={"name": "   "})
    assert r.status_code == 400
    print("PASS: create project requires non-empty name")


def test_list_projects_returns_user_projects():
    client = fresh_client()
    client.post("/api/projects", json={"name": "Acme"})
    client.post("/api/projects", json={"name": "Globex"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.get_json()]
    assert "Acme" in names and "Globex" in names
    print("PASS: list projects returns the user's projects")


def test_get_project_returns_documents_array():
    client = fresh_client()
    r = client.post("/api/projects", json={"name": "Has Docs"})
    proj_id = r.get_json()["id"]
    client.post(
        "/api/documents",
        json={"title": "Contract", "content": "draft", "project_id": proj_id},
    )
    r = client.get(f"/api/projects/{proj_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Has Docs"
    titles = [d["title"] for d in data["documents"]]
    assert "Contract" in titles
    print("PASS: get project returns its documents")


def test_rename_project():
    client = fresh_client()
    r = client.post("/api/projects", json={"name": "Old Name"})
    proj_id = r.get_json()["id"]
    r = client.patch(f"/api/projects/{proj_id}", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.get_json()["name"] == "New Name"
    print("PASS: rename project")


def test_delete_project_cascades_documents():
    client = fresh_client()
    r = client.post("/api/projects", json={"name": "Temp"})
    proj_id = r.get_json()["id"]
    r = client.post(
        "/api/documents",
        json={"title": "Will Die", "content": "x", "project_id": proj_id},
    )
    doc_id = r.get_json()["id"]

    r = client.delete(f"/api/projects/{proj_id}")
    assert r.status_code == 204

    r = client.get(f"/api/projects/{proj_id}")
    assert r.status_code == 404
    r = client.get(f"/api/documents/{doc_id}")
    assert r.status_code == 404
    print("PASS: delete project cascades to its documents")


def test_cannot_access_other_users_project():
    client = fresh_client()
    r = client.post("/api/projects", json={"name": "Frank Only"})
    frank_proj_id = r.get_json()["id"]

    # logout frank, register + login as alice
    client.post("/api/auth/logout")
    register_and_login(client, "alice@example.com", "Alice", "Smith")

    r = client.get(f"/api/projects/{frank_proj_id}")
    assert r.status_code == 403, r.get_json()
    r = client.delete(f"/api/projects/{frank_proj_id}")
    assert r.status_code == 403, r.get_json()
    print("PASS: cross-user project access is denied")


def test_create_document_without_project_uses_default():
    """backward compat: posting to /api/documents without a project_id
    drops the doc into the caller's default workspace."""
    client = fresh_client()
    r = client.post("/api/documents", json={"title": "Floaty", "content": ""})
    assert r.status_code == 201
    data = r.get_json()
    assert data["project_id"] is not None
    print("PASS: document creation falls back to the default project")


if __name__ == "__main__":
    try:
        test_create_project()
        test_create_project_requires_name()
        test_list_projects_returns_user_projects()
        test_get_project_returns_documents_array()
        test_rename_project()
        test_delete_project_cascades_documents()
        test_cannot_access_other_users_project()
        test_create_document_without_project_uses_default()
        print("\nall project tests passed!")
    finally:
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
            os.rmdir(_test_dir)
        except OSError:
            pass
