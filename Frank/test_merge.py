import os
import sys
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app  # noqa: E402
from models import db, Branch, Commit  # noqa: E402
from testing_helpers import register_test_user  # noqa: E402
from utils import reconstruct_branch_content  # noqa: E402


class MergeRouteTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        register_test_user(self.client)

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

    # ── Clean merge (unchanged from before) ────────────────────────

    def test_clean_merge_overwrites_main_and_archives_branch(self):
        document = self._create_document("Base terms")
        branch = self._create_branch(document["id"])
        incoming_content = "Base terms\nAdded indemnity clause"
        self._commit(branch["id"], incoming_content)

        response = self.client.post(f"/api/branches/{branch['id']}/merge")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["branch_status"], "deleted")
        self.assertEqual(payload["main_content"], incoming_content)
        self.assertIsNotNone(payload["merge_commit_id"])

        with self.app.app_context():
            # Branch should be deleted from DB
            merged_branch = db.session.get(Branch, branch["id"])
            self.assertIsNone(merged_branch)

            main_branch = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first()
            merge_commit = db.session.get(Commit, payload["merge_commit_id"])

            self.assertEqual(merge_commit.branch_id, main_branch.id)
            self.assertEqual(reconstruct_branch_content(main_branch), incoming_content)

        # Branch no longer exists — committing to it returns 404
        rejected = self.client.post(
            f"/api/branches/{branch['id']}/commits",
            json={"message": "Late edit", "content": "Should not save"},
        )
        self.assertEqual(rejected.status_code, 404)

    # ── Diverged: merge without resolutions → 409 with conflict flag ──

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
        payload = response.get_json()
        self.assertTrue(payload.get("conflict"))

        with self.app.app_context():
            merged_branch = db.session.get(Branch, branch["id"])
            main_branch = db.session.get(Branch, main_branch_id)

            self.assertEqual(merged_branch.status, "active")
            self.assertEqual(reconstruct_branch_content(main_branch), "Main changed")

    # ── Merge preview ──────────────────────────────────────────────

    def test_merge_preview_no_divergence(self):
        """Preview when Main hasn't diverged — all auto-branch or equal."""
        document = self._create_document("Base terms")
        branch = self._create_branch(document["id"])
        self._commit(branch["id"], "Base terms\nNew clause")

        response = self.client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertFalse(payload["has_conflicts"])
        self.assertIsInstance(payload["hunks"], list)
        self.assertTrue(len(payload["hunks"]) > 0)

    def test_merge_preview_with_conflicts(self):
        """Preview when both sides changed the same line → conflict."""
        document = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_branch_id, "line one\nMAIN edit\nline three")

        response = self.client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertTrue(payload["has_conflicts"])
        conflict_hunks = [h for h in payload["hunks"] if h["kind"] == "conflict"]
        self.assertTrue(len(conflict_hunks) >= 1)

    def test_merge_preview_non_overlapping(self):
        """Preview when changes are on different lines → no conflicts."""
        document = self._create_document(
            "line one\nline two\nline three\nline four\nline five"
        )
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        # Branch changes line 2, Main changes line 4
        self._commit(branch["id"], "line one\nBRANCH\nline three\nline four\nline five")
        self._commit(main_branch_id, "line one\nline two\nline three\nMAIN\nline five")

        response = self.client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertFalse(payload["has_conflicts"])

    # ── Merge with resolutions ─────────────────────────────────────

    def test_merge_with_resolutions_pick_main(self):
        """Resolve conflict by picking Main side."""
        document = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_branch_id, "line one\nMAIN edit\nline three")

        # Get preview to find conflict hunk IDs
        preview = self.client.get(
            f"/api/branches/{branch['id']}/merge/preview"
        ).get_json()
        conflict_hunks = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        resolutions = {h["id"]: "main" for h in conflict_hunks}

        # Merge with resolutions
        response = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["branch_status"], "deleted")
        self.assertIn("MAIN edit", payload["main_content"])

    def test_merge_with_resolutions_pick_branch(self):
        """Resolve conflict by picking branch side."""
        document = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_branch_id, "line one\nMAIN edit\nline three")

        preview = self.client.get(
            f"/api/branches/{branch['id']}/merge/preview"
        ).get_json()
        conflict_hunks = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        resolutions = {h["id"]: "branch" for h in conflict_hunks}

        response = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["branch_status"], "deleted")
        self.assertIn("BRANCH edit", payload["main_content"])

    def test_merge_with_missing_resolutions_returns_400(self):
        """Merge fails if not all conflict hunks have resolutions."""
        document = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_branch_id, "line one\nMAIN edit\nline three")

        response = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": {}},  # Empty — missing conflict resolutions
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing resolutions", response.get_json()["error"])

    def test_merge_with_custom_resolution(self):
        """Resolve conflict with custom text."""
        document = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(document["id"])

        with self.app.app_context():
            main_branch_id = Branch.query.filter_by(
                document_id=document["id"], is_main=True
            ).first().id

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_branch_id, "line one\nMAIN edit\nline three")

        preview = self.client.get(
            f"/api/branches/{branch['id']}/merge/preview"
        ).get_json()
        conflict_hunks = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        resolutions = {h["id"]: {"custom": "CUSTOM resolution"} for h in conflict_hunks}

        response = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("CUSTOM resolution", payload["main_content"])


if __name__ == "__main__":
    unittest.main()
