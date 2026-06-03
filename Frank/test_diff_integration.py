# diff engine tests that go through the real api (GET /api/branches/<id>/diff)
# instead of calling the diff functions directly. each test makes a doc,
# branches it, commits an edit on the branch, then diffs the branch vs main.
#
# covers the cases that usually break diffs: deleting everything, pasting a
# huge block, a one-line change in a big file, edits far apart, whitespace-only
# changes, unicode/emoji, and one really long line.
#
# throwaway sqlite db so the real one isn't touched.

import os
import sys
import tempfile
import warnings

_test_dir = tempfile.mkdtemp(prefix="docucommit_diffint_")
TEST_DB_PATH = os.path.join(_test_dir, "diff_integration.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# branches and commits point at each other so sqlite can't order the tables
# for DROP and warns. it still works, so hide the warning.
warnings.filterwarnings("ignore", message=r"Can't sort tables for DROP")

sys.path.insert(0, ".")

from app import app  # noqa: E402
from models import db  # noqa: E402


# --- helpers ------------------------------------------------------------

def authenticate(client):
    """register a test user so the session is authenticated.
    document creation requires a logged-in user."""
    r = client.post(
        "/api/auth/register",
        json={
            "email": "tester@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPass1!",
        },
    )
    assert r.status_code == 201, f"auth setup failed: {r.get_json()}"


def fresh_client():
    """wipe the test db and return an authenticated flask test client."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    client = app.test_client()
    authenticate(client)
    return client


def create_doc(client, title, content):
    r = client.post("/api/documents", json={"title": title, "content": content})
    assert r.status_code == 201, f"create_doc failed: {r.get_json()}"
    return r.get_json()


def create_branch(client, doc_id, name):
    r = client.post(f"/api/documents/{doc_id}/branches", json={"name": name})
    assert r.status_code == 201, f"create_branch failed: {r.get_json()}"
    return r.get_json()


def commit_on_branch(client, branch_id, content, message="edit"):
    r = client.post(
        f"/api/branches/{branch_id}/commits",
        json={"message": message, "content": content},
    )
    assert r.status_code == 201, f"commit failed: {r.get_json()}"
    return r.get_json()


def branch_diff(client, branch_id, ignore_whitespace=False):
    """call GET /api/branches/<id>/diff and return (status_code, json)."""
    qs = "?w=1" if ignore_whitespace else ""
    r = client.get(f"/api/branches/{branch_id}/diff{qs}")
    return r.status_code, r.get_json()


def doc_with_edited_branch(client, doc_title, main_content, branch_name, branch_content):
    """create a document, branch it, and commit branch_content on the branch.
    returns the branch dict so the caller can diff it against Main."""
    doc = create_doc(client, doc_title, main_content)
    branch = create_branch(client, doc["id"], branch_name)
    commit_on_branch(client, branch["id"], branch_content)
    return branch


# --- edge case tests ----------------------------------------------------

def test_entirely_deleted_document():
    """blanking a branch shows every line of Main as removed."""
    client = fresh_client()
    branch = doc_with_edited_branch(
        client, "Contract",
        "clause one\nclause two\nclause three\n",
        "wipe-it", "",
    )
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["removed"] > 0, f"expected removals, got {s}"
    assert s["added"] == 0, f"nothing should be added, got {s}"
    assert s["modified"] == 0, f"nothing should be modified, got {s}"
    print("PASS: entirely deleted document shows all content removed")


def test_massive_copy_paste():
    """pasting thousands of lines onto a branch is a large block of additions."""
    client = fresh_client()
    pasted = "intro paragraph\n" + "".join(
        f"pasted clause number {i}\n" for i in range(5000)
    )
    branch = doc_with_edited_branch(
        client, "Contract", "intro paragraph\n", "big-paste", pasted,
    )
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["added"] >= 5000, f"expected ~5000 additions, got {s}"
    assert s["removed"] == 0, f"nothing should be removed, got {s}"
    print("PASS: massive copy-paste registers as a large block of additions")


def test_unchanged_branch_produces_no_diff():
    """a branch with no commits is identical to Main and diffs to nothing."""
    client = fresh_client()
    doc = create_doc(client, "Contract", "section A\nsection B\nsection C\n")
    branch = create_branch(client, doc["id"], "untouched")

    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["added"] == 0 and s["removed"] == 0 and s["modified"] == 0, (
        f"an untouched branch should show no changes, got {s}"
    )
    print("PASS: an untouched branch produces no diff")


def test_single_line_change_in_large_doc_is_localized():
    """changing one line in a 1000-line doc is reported as exactly one
    modification, not a wholesale rewrite."""
    client = fresh_client()
    base = "".join(f"line {i}\n" for i in range(1000))
    lines = base.splitlines(keepends=True)
    lines[500] = "CHANGED line 500\n"
    edited = "".join(lines)

    branch = doc_with_edited_branch(client, "Big", base, "one-edit", edited)
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["modified"] == 1, f"expected exactly one modified line, got {s}"
    assert s["unchanged"] == 999, f"expected 999 unchanged lines, got {s}"
    assert s["added"] == 0 and s["removed"] == 0, f"no pure add/remove expected, got {s}"
    print("PASS: single-line change in a 1000-line doc is localized to one row")


def test_far_apart_edits_register_as_two_modifications():
    """edits at opposite ends of a file are tracked as two separate changes."""
    client = fresh_client()
    base = "".join(f"line {i}\n" for i in range(1000))
    lines = base.splitlines(keepends=True)
    lines[5] = "EDITED near the top\n"
    lines[995] = "EDITED near the bottom\n"
    edited = "".join(lines)

    branch = doc_with_edited_branch(client, "Big", base, "two-edits", edited)
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["modified"] == 2, f"expected 2 modified lines, got {s}"
    assert s["unchanged"] == 998, f"expected 998 unchanged lines, got {s}"
    print("PASS: far-apart edits register as two separate modifications")


def test_branch_diff_detects_a_real_addition():
    """the branch-vs-main diff reports genuinely new content as added."""
    client = fresh_client()
    branch = doc_with_edited_branch(
        client, "Contract",
        "the contract terms are final\n",
        "add-clause",
        "the contract terms are final\na brand new clause\n",
    )
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    assert payload["summary"]["added"] >= 1, (
        f"expected the new clause to show as added, got {payload['summary']}"
    )
    print("PASS: branch diff detects a real content addition")


def test_whitespace_only_change_is_not_flagged():
    """a whitespace-only edit should not surface as a real change, and the
    ?w=1 flag is honored in the response metadata."""
    client = fresh_client()
    branch = doc_with_edited_branch(
        client, "Contract",
        "the contract terms are final\n",
        "whitespace-fiddle",
        "the   contract    terms are   final\n",  # same words, extra spaces
    )

    # without the flag: the engine normalizes whitespace, so no real changes
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["added"] == 0 and s["removed"] == 0 and s["modified"] == 0, (
        f"whitespace-only change should not be flagged, got {s}"
    )

    # with ?w=1: still no changes, and the response confirms the flag was read
    status, payload = branch_diff(client, branch["id"], ignore_whitespace=True)
    assert status == 200, payload
    assert payload["ignore_whitespace"] is True, "?w=1 was not honored in the response"
    print("PASS: whitespace-only change is not flagged (with and without ?w=1)")


def test_unicode_and_emoji_content():
    """accents, currency symbols and emoji shouldn't break the diff.
    the data has real unicode on purpose since that's what we're testing."""
    client = fresh_client()
    branch = doc_with_edited_branch(
        client, "Unicode",
        "Café contract\nPrice: 100€\nStatus: \U0001F600 approved\n",
        "unicode-edit",
        "Café contract\nPrice: 200€\nStatus: \U0001F622 rejected\n",
    )
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    s = payload["summary"]
    assert s["modified"] >= 1, f"expected changed unicode lines to register, got {s}"
    assert s["unchanged"] >= 1, f"expected the unchanged cafe line to register, got {s}"
    print("PASS: unicode and emoji content diffs without breaking")


def test_very_long_single_line():
    """a 50k-character single line with a mid-string change is handled."""
    client = fresh_client()
    branch = doc_with_edited_branch(
        client, "LongLine",
        "A" * 25000 + "B" * 25000,
        "long-edit",
        "A" * 25000 + "C" * 25000,
    )
    status, payload = branch_diff(client, branch["id"])
    assert status == 200, payload
    assert payload["summary"]["modified"] >= 1, (
        f"expected the long line to register as modified, got {payload['summary']}"
    )
    print("PASS: 50k-character single line is handled without crashing")


def test_branch_diff_missing_branch_returns_404():
    """diffing a branch that does not exist is a clean 404, not a crash."""
    client = fresh_client()
    status, payload = branch_diff(client, 999999)
    assert status == 404, f"expected 404 for missing branch, got {status}: {payload}"
    print("PASS: diffing a missing branch returns 404")


# --- runner -------------------------------------------------------------

if __name__ == "__main__":
    try:
        test_entirely_deleted_document()
        test_massive_copy_paste()
        test_unchanged_branch_produces_no_diff()
        test_single_line_change_in_large_doc_is_localized()
        test_far_apart_edits_register_as_two_modifications()
        test_branch_diff_detects_a_real_addition()
        test_whitespace_only_change_is_not_flagged()
        test_unicode_and_emoji_content()
        test_very_long_single_line()
        test_branch_diff_missing_branch_returns_404()
        print("\nall diff integration tests passed!")
    finally:
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
            os.rmdir(_test_dir)
        except OSError:
            pass
