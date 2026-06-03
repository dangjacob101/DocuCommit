import os
import sys
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, Branch, Commit
from utils import reconstruct_branch_content


class SafeMergeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            from app import _seed_default_user
            _seed_default_user()
        self._login()

    def _login(self):
        self.client.post(
            "/api/auth/login",
            json={"email": "frank@docucommit.com", "password": "CS35LTeamprofile!"},
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _create_document(self, content="Base text"):
        r = self.client.post("/api/documents", json={"title": "TestDoc", "content": content})
        self.assertEqual(r.status_code, 201)
        return r.get_json()

    def _create_branch(self, document_id, name="feature"):
        r = self.client.post(f"/api/documents/{document_id}/branches", json={"name": name})
        self.assertEqual(r.status_code, 201)
        return r.get_json()

    def _commit(self, branch_id, content, message="edit"):
        r = self.client.post(
            f"/api/branches/{branch_id}/commits",
            json={"message": message, "content": content},
        )
        self.assertEqual(r.status_code, 201)
        return r.get_json()

    def _main_branch_id(self, document_id):
        with self.app.app_context():
            return Branch.query.filter_by(
                document_id=document_id, is_main=True
            ).first().id

    def test_linear_fast_forward(self):
        doc = self._create_document("Hello world")
        branch = self._create_branch(doc["id"])
        self._commit(branch["id"], "Hello world\nNew line added")

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 200)
        payload = r.get_json()
        self.assertEqual(payload["branch_status"], "deleted")
        self.assertIn("New line added", payload["main_content"])

    def test_diverged_rejects_without_resolutions(self):
        doc = self._create_document("Base text")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "Branch version")
        self._commit(main_id, "Main version")

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.get_json().get("conflict"))

    def test_diverged_non_overlapping_auto_resolves(self):
        doc = self._create_document("line one\nline two\nline three\nline four\nline five")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nBRANCH\nline three\nline four\nline five")
        self._commit(main_id, "line one\nline two\nline three\nline four\nMAIN")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        self.assertFalse(preview["has_conflicts"])

        r = self.client.post(f"/api/branches/{branch['id']}/merge", json={"resolutions": {}})
        self.assertEqual(r.status_code, 200)
        content = r.get_json()["main_content"]
        self.assertIn("BRANCH", content)
        self.assertIn("MAIN", content)

    def test_diverged_overlapping_produces_conflict(self):
        doc = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nBRANCH edit\nline three")
        self._commit(main_id, "line one\nMAIN edit\nline three")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        self.assertTrue(preview["has_conflicts"])
        conflicts = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        self.assertGreaterEqual(len(conflicts), 1)

    def test_adjacent_edits_preserved(self):
        doc = self._create_document("A\nB\nC\nD\nE")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "A\nB-branch\nC\nD\nE")
        self._commit(main_id, "A\nB\nC\nD-main\nE")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        self.assertFalse(preview["has_conflicts"])

    def test_identical_edits_auto_resolve(self):
        doc = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nSAME EDIT\nline three")
        self._commit(main_id, "line one\nSAME EDIT\nline three")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        self.assertFalse(preview["has_conflicts"])

    def test_branch_additions_at_end(self):
        doc = self._create_document("First line")
        branch = self._create_branch(doc["id"])

        self._commit(branch["id"], "First line\nSecond line\nThird line")

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Third line", r.get_json()["main_content"])

    def test_main_additions_at_end(self):
        doc = self._create_document("A\nB\nC")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "A\nB-edited\nC")
        self._commit(main_id, "A\nB\nC\nD-appended")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        self.assertFalse(preview["has_conflicts"])

    def test_empty_branch_merge_rejected(self):
        doc = self._create_document("Hello")
        branch = self._create_branch(doc["id"])

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no changes", r.get_json()["error"])

    def test_already_merged_branch_rejected(self):
        doc = self._create_document("Hello")
        branch = self._create_branch(doc["id"])
        self._commit(branch["id"], "Hello world")

        r1 = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r2.status_code, 404)

    def test_merge_preview_on_merged_branch_rejected(self):
        doc = self._create_document("Hello")
        branch = self._create_branch(doc["id"])
        self._commit(branch["id"], "Hello world")
        self.client.post(f"/api/branches/{branch['id']}/merge")

        r = self.client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(r.status_code, 404)

    def test_resolution_with_all_three_options(self):
        doc = self._create_document("A\nB\nC\nD\nE\nF\nG")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "A\nB-branch\nC\nD-branch\nE\nF-branch\nG")
        self._commit(main_id, "A\nB-main\nC\nD-main\nE\nF-main\nG")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        conflicts = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        self.assertGreaterEqual(len(conflicts), 1)

        resolutions = {}
        for i, c in enumerate(conflicts):
            if i % 3 == 0:
                resolutions[c["id"]] = "main"
            elif i % 3 == 1:
                resolutions[c["id"]] = "branch"
            else:
                resolutions[c["id"]] = {"custom": "CUSTOM"}

        r = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["branch_status"], "deleted")

    def test_merge_preserves_main_history(self):
        doc = self._create_document("Start")
        main_id = self._main_branch_id(doc["id"])
        self._commit(main_id, "Start\nSecond commit")

        with self.app.app_context():
            commits_before = Commit.query.filter_by(branch_id=main_id).count()

        branch = self._create_branch(doc["id"])
        self._commit(branch["id"], "Start\nSecond commit\nBranch addition")
        self.client.post(f"/api/branches/{branch['id']}/merge")

        with self.app.app_context():
            commits_after = Commit.query.filter_by(branch_id=main_id).count()

        self.assertEqual(commits_after, commits_before + 1)

    def test_merge_does_not_affect_sibling_branches(self):
        doc = self._create_document("Original")
        branch_a = self._create_branch(doc["id"], "branch-a")
        branch_b = self._create_branch(doc["id"], "branch-b")

        self._commit(branch_a["id"], "Original\nFrom A")
        self._commit(branch_b["id"], "Original\nFrom B")

        b_before = self.client.get(f"/api/branches/{branch_b['id']}").get_json()["current_content"]

        self.client.post(f"/api/branches/{branch_a['id']}/merge")

        b_after = self.client.get(f"/api/branches/{branch_b['id']}").get_json()["current_content"]
        self.assertEqual(b_before, b_after)

    def test_multi_conflict_resolution(self):
        doc = self._create_document("A\nB\nC\nD\nE")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "A-branch\nB\nC-branch\nD\nE-branch")
        self._commit(main_id, "A-main\nB\nC-main\nD\nE-main")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        conflicts = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        self.assertGreaterEqual(len(conflicts), 1)

        resolutions = {c["id"]: "main" for c in conflicts}
        r = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(r.status_code, 200)
        content = r.get_json()["main_content"]
        self.assertIn("main", content)
        self.assertNotIn("branch", content)

    def test_preview_includes_summary_and_progression(self):
        doc = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nBRANCH\nline three")
        self._commit(main_id, "line one\nMAIN\nline three")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()

        self.assertIn("summary", preview)
        self.assertIn("progression", preview)
        self.assertGreater(preview["summary"]["total_hunks"], 0)
        self.assertTrue(preview["progression"]["main_diverged"])

    def test_merge_unauthenticated_rejected(self):
        doc = self._create_document("Hello")
        branch = self._create_branch(doc["id"])
        client = self.app.test_client()

        r1 = client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(r1.status_code, 401)

        r2 = client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r2.status_code, 401)

    def test_merge_unauthorized_rejected(self):
        doc = self._create_document("Hello")
        branch = self._create_branch(doc["id"])
        client = self.app.test_client()
        r_reg = client.post(
            "/api/auth/register",
            json={
                "email": "alice@docucommit.com",
                "first_name": "Alice",
                "last_name": "User",
                "password": "CS35LTeamprofile2!",
            },
        )
        self.assertEqual(r_reg.status_code, 201)

        r1 = client.get(f"/api/branches/{branch['id']}/merge/preview")
        self.assertEqual(r1.status_code, 403)

        r2 = client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r2.status_code, 403)

    def test_mid_file_insertion_preserved(self):
        doc = self._create_document("line one\nline two")
        branch = self._create_branch(doc["id"])
        self._commit(branch["id"], "line one\ninserted\nline two")

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 200)
        self.assertIn("inserted", r.get_json()["main_content"])

    def test_invalid_custom_resolution_type_rejected(self):
        doc = self._create_document("line one\nline two")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nBRANCH\nline two")
        self._commit(main_id, "line one\nMAIN\nline two")

        preview = self.client.get(f"/api/branches/{branch['id']}/merge/preview").get_json()
        conflicts = [h for h in preview["hunks"] if h["kind"] == "conflict"]
        self.assertGreaterEqual(len(conflicts), 1)

        resolutions = {conflicts[0]["id"]: {"custom": 123}}
        r = self.client.post(
            f"/api/branches/{branch['id']}/merge",
            json={"resolutions": resolutions},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("must be a string", r.get_json()["error"])

    def test_clean_diverged_merge_auto_succeeds(self):
        doc = self._create_document("line one\nline two\nline three")
        branch = self._create_branch(doc["id"])
        main_id = self._main_branch_id(doc["id"])

        self._commit(branch["id"], "line one\nBRANCH\nline three")
        self._commit(main_id, "MAIN\nline two\nline three")

        r = self.client.post(f"/api/branches/{branch['id']}/merge")
        self.assertEqual(r.status_code, 200)
        content = r.get_json()["main_content"]
        self.assertIn("BRANCH", content)
        self.assertIn("MAIN", content)


if __name__ == "__main__":
    unittest.main()
