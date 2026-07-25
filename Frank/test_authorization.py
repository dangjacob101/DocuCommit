import os
import sys
import unittest
import warnings

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.exc import SAWarning  # noqa: E402

warnings.filterwarnings(
    "ignore",
    message=r"Can't sort tables for DROP",
    category=SAWarning,
)

from app import create_app  # noqa: E402
from models import db, User  # noqa: E402
from testing_helpers import register_test_user  # noqa: E402


class DataRouteAuthorizationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

        registration = register_test_user(self.client)
        self.owner_id = registration.get_json()["user"]["id"]
        document_response = self.client.post(
            "/api/documents",
            json={"title": "Private contract", "content": "Original terms"},
        )
        self.assertEqual(document_response.status_code, 201)
        self.document_id = document_response.get_json()["id"]

        branch_response = self.client.post(
            f"/api/documents/{self.document_id}/branches",
            json={"name": "Negotiation"},
        )
        self.assertEqual(branch_response.status_code, 201)
        self.branch_id = branch_response.get_json()["id"]

        commit_response = self.client.post(
            f"/api/branches/{self.branch_id}/commits",
            json={"message": "Revise terms", "content": "Revised terms"},
        )
        self.assertEqual(commit_response.status_code, 201)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _protected_requests(self, client):
        return [
            client.get(f"/api/documents/{self.document_id}/commits"),
            client.get(f"/api/documents/{self.document_id}/export"),
            client.get(f"/api/auth/profile-picture/{self.owner_id}"),
            client.get(f"/api/documents/{self.document_id}/branches"),
            client.post(
                f"/api/documents/{self.document_id}/branches",
                json={"name": "Unauthorized branch"},
            ),
            client.get(f"/api/branches/{self.branch_id}"),
            client.get(f"/api/branches/{self.branch_id}/commits"),
            client.post(
                f"/api/branches/{self.branch_id}/commits",
                json={"message": "Unauthorized", "content": "Stolen edit"},
            ),
            client.get(f"/api/branches/{self.branch_id}/diff"),
        ]

    def test_startup_does_not_create_a_shared_account(self):
        isolated_app = create_app()
        with isolated_app.app_context():
            self.assertEqual(User.query.count(), 0)

    def test_data_routes_reject_unauthenticated_clients(self):
        unauthenticated = self.app.test_client()
        for response in self._protected_requests(unauthenticated):
            with self.subTest(path=response.request.path):
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.get_json(),
                    {"error": "authentication required"},
                )

    def test_data_routes_reject_other_users(self):
        other_user = self.app.test_client()
        register_test_user(other_user, email="other@example.com")

        for response in self._protected_requests(other_user):
            with self.subTest(path=response.request.path):
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json(), {"error": "access denied"})

    def test_password_login_rejects_oauth_only_account(self):
        with self.app.app_context():
            db.session.add(
                User(
                    email="oauth@example.com",
                    first_name="OAuth",
                    last_name="User",
                    google_id="oauth-subject",
                    hashed_password=None,
                )
            )
            db.session.commit()

        response = self.app.test_client().post(
            "/api/auth/login",
            json={"email": "oauth@example.com", "password": "TestPass1!"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json(),
            {"error": "Invalid email or password"},
        )

    def test_owner_retains_access(self):
        expected_statuses = [
            self.client.get(f"/api/documents/{self.document_id}/commits"),
            self.client.get(f"/api/documents/{self.document_id}/export"),
            self.client.get(f"/api/documents/{self.document_id}/branches"),
            self.client.get(f"/api/branches/{self.branch_id}"),
            self.client.get(f"/api/branches/{self.branch_id}/commits"),
            self.client.get(f"/api/branches/{self.branch_id}/diff"),
        ]
        for response in expected_statuses:
            with self.subTest(path=response.request.path):
                self.assertEqual(response.status_code, 200)

        missing_picture = self.client.get(
            f"/api/auth/profile-picture/{self.owner_id}"
        )
        self.assertEqual(missing_picture.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
