import os
import sys
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app  # noqa: E402
from models import db, Branch, Commit  # noqa: E402
from utils import reconstruct_branch_content  # noqa: E402


class MergeRouteTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        self.client.post(
            "/api/auth/register",
            json={"username": "merge_test", "password": "MergeTest1!"},
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_document(self, content="Base text"):
        response = self.client.post(
            "/api/documents",
            json={"title": "Contract", "content": content},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _create_branch(self, document_id, name="Negotiated"):
        response = self.client.post(
            f"/api/documents/{document_id}/branches",
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def _commit(self, branch_id, content, message="Revision"):
        response = self.client.post(
            f"/api/branches/{branch_id}/commits",
            json={"message": message, "content": content},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_clean_merge_overwrites_main_and_archives_branch(self):
        document = self._create_document("Base terms")
        branch = self._create_branch(document["id"])
        incoming_content = "Base terms\nAdded indemnity clause"
        self._commit(branch["id"], incoming_content)

        response = self.client.post(f"/api/branches/{branch['id']}/merge")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["branch_status"], "merged")
        self.assertEqual(payload["main_content"], incoming_content)
        self.assertIsNotNone(payload["merge_commit_id"])

        with self.app.app_context():
            merged_branch = db.session.get(Branch, branch["id"])
            main_branch = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first()
            merge_commit = db.session.get(Commit, payload["merge_commit_id"])

            self.assertEqual(merged_branch.status, "merged")
            self.assertEqual(merge_commit.branch_id, main_branch.id)
            self.assertEqual(reconstruct_branch_content(main_branch), incoming_content)

        rejected = self.client.post(
            f"/api/branches/{branch['id']}/commits",
            json={"message": "Late edit", "content": "Should not save"},
        )
        self.assertEqual(rejected.status_code, 409)

    def test_merge_rejects_when_main_has_new_commits(self):
        document = self._create_document("Base terms")
        branch = self._create_branch(document["id"])
        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "Branch version")
        self._commit(main_branch_id, "Main changed")

        response = self.client.post(f"/api/branches/{branch['id']}/merge")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Main has diverged", response.get_json()["error"])

        with self.app.app_context():
            merged_branch = db.session.get(Branch, branch["id"])
            main_branch = db.session.get(Branch, main_branch_id)

            self.assertEqual(merged_branch.status, "active")
            self.assertEqual(reconstruct_branch_content(main_branch), "Main changed")


if __name__ == "__main__":
    unittest.main()
