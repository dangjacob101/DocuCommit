# test_branch_isolation.py — week 5 deliverable
#
# proves that edits made on a feature branch never mutate the Main branch.
# uses flask's test_client + a temp sqlite db so each run starts clean
# and the dev db (documents.db) is never touched.

import os
import sys
import tempfile
import warnings

# point the app at an isolated test db before importing it.
# we use a real file (not :memory:) because sqlite in-memory dbs are
# per-connection — different requests would otherwise see different dbs.
_test_dir = tempfile.mkdtemp(prefix="docucommit_isolation_")
TEST_DB_PATH = os.path.join(_test_dir, "isolation.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

# branches and commits reference each other (branch.branched_from_commit_id
# points at commits.id, commits.branch_id points at branches.id). sqlite
# can't ALTER to break that cycle on DROP, so sqlalchemy warns. the drop
# still works; just silence the noise so test output stays readable.
warnings.filterwarnings(
    "ignore",
    message=r"Can't sort tables for DROP",
)

sys.path.insert(0, ".")

from app import app  # noqa: E402  (must come after env var is set)
from models import db  # noqa: E402


# --- helpers ------------------------------------------------------------

def fresh_client():
    """wipe and rebuild the test db, return a flask test client."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app.test_client()


def create_doc(client, title="Test Doc", content="initial main text"):
    r = client.post("/api/documents", json={"title": title, "content": content})
    assert r.status_code == 201, f"create_doc failed: {r.get_json()}"
    return r.get_json()


def list_branches(client, doc_id):
    r = client.get(f"/api/documents/{doc_id}/branches")
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def get_main_branch(client, doc_id):
    for b in list_branches(client, doc_id):
        if b["is_main"]:
            return b
    raise AssertionError("main branch not found for doc")


def main_content(client, doc_id):
    return get_main_branch(client, doc_id)["current_content"]


def create_branch(client, doc_id, name, source_branch_id=None):
    body = {"name": name}
    if source_branch_id is not None:
        body["source_branch_id"] = source_branch_id
    r = client.post(f"/api/documents/{doc_id}/branches", json=body)
    assert r.status_code == 201, f"create_branch failed: {r.get_json()}"
    return r.get_json()


def commit_on_branch(client, branch_id, content, message="edit"):
    r = client.post(
        f"/api/branches/{branch_id}/commits",
        json={"message": message, "content": content},
    )
    assert r.status_code == 201, f"commit failed: {r.get_json()}"
    return r.get_json()


def get_branch(client, branch_id):
    r = client.get(f"/api/branches/{branch_id}")
    assert r.status_code == 200, r.get_json()
    return r.get_json()


# --- tests --------------------------------------------------------------

def test_creating_branch_does_not_change_main():
    client = fresh_client()
    doc = create_doc(client, content="original main content")
    before = main_content(client, doc["id"])

    create_branch(client, doc["id"], "feature-1")

    after = main_content(client, doc["id"])
    assert before == after, f"main changed after branch create: {before!r} -> {after!r}"
    print("PASS: creating a branch leaves Main untouched")


def test_committing_on_branch_does_not_change_main():
    client = fresh_client()
    doc = create_doc(client, content="original main content")
    main_before = main_content(client, doc["id"])

    branch = create_branch(client, doc["id"], "feature-1")
    commit_on_branch(client, branch["id"], "completely different feature-branch text")

    main_after = main_content(client, doc["id"])
    assert main_before == main_after, (
        f"main mutated by a branch commit: {main_before!r} -> {main_after!r}"
    )
    print("PASS: a single commit on a branch leaves Main untouched")


def test_many_commits_on_branch_do_not_touch_main():
    client = fresh_client()
    doc = create_doc(client, content="main start")
    main_before = main_content(client, doc["id"])

    branch = create_branch(client, doc["id"], "long-running")
    content = "main start"
    for i in range(10):
        content += f"\nedit number {i}"
        commit_on_branch(client, branch["id"], content, message=f"edit {i}")

    main_after = main_content(client, doc["id"])
    assert main_before == main_after, "main moved after 10 branch commits"
    print("PASS: 10 commits on a branch leave Main untouched")


def test_sibling_branches_do_not_bleed_into_each_other():
    client = fresh_client()
    doc = create_doc(client, content="shared starting text")

    branch_a = create_branch(client, doc["id"], "feature-a")
    branch_b = create_branch(client, doc["id"], "feature-b")
    main_before = main_content(client, doc["id"])

    # only branch A receives edits
    commit_on_branch(client, branch_a["id"], "feature A's revised text")

    # branch B should still match Main, totally unaware of A's work
    b_after = get_branch(client, branch_b["id"])["current_content"]
    main_after = main_content(client, doc["id"])
    assert main_before == main_after, "main mutated while editing sibling branch A"
    assert b_after == main_after, (
        f"branch B drifted because of edits on sibling A: B={b_after!r} main={main_after!r}"
    )
    print("PASS: sibling branches stay isolated from each other")


def test_main_edits_after_fork_do_not_change_existing_branches():
    client = fresh_client()
    doc = create_doc(client, content="initial main draft")

    branch = create_branch(client, doc["id"], "feature-snapshot")
    branch_at_fork = get_branch(client, branch["id"])["current_content"]

    # advance main with a PUT /api/documents/<id>
    r = client.put(
        f"/api/documents/{doc['id']}",
        json={"content": "main has moved on without the branch"},
    )
    assert r.status_code == 200, r.get_json()

    branch_now = get_branch(client, branch["id"])["current_content"]
    assert branch_at_fork == branch_now, (
        f"branch drifted when main was edited: before={branch_at_fork!r} after={branch_now!r}"
    )
    print("PASS: editing Main after fork does not move the existing branch")


def test_branch_of_branch_does_not_affect_either_ancestor():
    client = fresh_client()
    doc = create_doc(client, content="root content")
    main_before = main_content(client, doc["id"])

    branch_b = create_branch(client, doc["id"], "feature-b")
    commit_on_branch(client, branch_b["id"], "root content\nedits from B")
    b_before = get_branch(client, branch_b["id"])["current_content"]

    # branch C off branch B
    branch_c = create_branch(client, doc["id"], "feature-c", source_branch_id=branch_b["id"])
    commit_on_branch(client, branch_c["id"], "root content\nedits from B\nedits from C")

    main_after = main_content(client, doc["id"])
    b_after = get_branch(client, branch_b["id"])["current_content"]
    assert main_before == main_after, "Main moved while C was being edited"
    assert b_before == b_after, "Branch B moved while its child C was being edited"
    print("PASS: child branch edits do not touch Main or the parent branch")


def test_diff_endpoint_is_read_only():
    client = fresh_client()
    doc = create_doc(client, content="original")
    branch = create_branch(client, doc["id"], "feature")
    commit_on_branch(client, branch["id"], "branch edit")

    main_before = main_content(client, doc["id"])
    branch_before = get_branch(client, branch["id"])["current_content"]

    # hit the diff endpoint several times — should never mutate state
    for _ in range(3):
        r = client.get(f"/api/branches/{branch['id']}/diff")
        assert r.status_code == 200, r.get_json()

    main_after = main_content(client, doc["id"])
    branch_after = get_branch(client, branch["id"])["current_content"]
    assert main_before == main_after, "diff endpoint mutated Main"
    assert branch_before == branch_after, "diff endpoint mutated the branch"
    print("PASS: hitting the diff endpoint does not mutate Main or the branch")


def test_main_byte_for_byte_unchanged_across_full_branch_lifecycle():
    """end-to-end: branch, 5 rounds of edits, abandon — Main must be bit-exact.

    note: apply_patch strips trailing newlines when reconstructing from an
    empty source, so we compare main-before to main-after (both go through
    the same pipeline) rather than to the raw input string. that's the
    correct isolation question anyway.
    """
    client = fresh_client()
    initial = "legal contract draft v1\nsection A\nsection B\n"
    doc = create_doc(client, content=initial)
    main_before = main_content(client, doc["id"])

    branch = create_branch(client, doc["id"], "lawyer-1-edits")
    drafts = [
        "legal contract draft v1\nsection A revised\nsection B\n",
        "legal contract draft v1\nsection A revised\nsection B (updated)\n",
        "legal contract draft v1\nsection A revised\nsection B (updated)\nsection C added\n",
        "legal contract draft v1\nsection A done\nsection B (updated)\nsection C added\n",
        "legal contract draft v1\nsection A done\nsection B final\nsection C added\nsection D\n",
    ]
    for d in drafts:
        commit_on_branch(client, branch["id"], d, message="lawyer edit")

    main_after = main_content(client, doc["id"])
    assert main_before == main_after, (
        f"main mutated during a full branch lifecycle.\nbefore: {main_before!r}\nafter:  {main_after!r}"
    )
    print("PASS: Main is byte-for-byte identical after a full branch edit lifecycle")


def test_main_commit_count_is_unchanged_by_branch_activity():
    """direct model-level check: Main's commit list does not grow when a branch commits."""
    client = fresh_client()
    doc = create_doc(client, content="hello")

    with app.app_context():
        from models import Branch, Commit
        main = Branch.query.filter_by(document_id=doc["id"], is_main=True).first()
        main_commit_ids_before = [c.id for c in Commit.query.filter_by(branch_id=main.id).all()]

    branch = create_branch(client, doc["id"], "noisy-branch")
    for i in range(5):
        commit_on_branch(client, branch["id"], f"branch text v{i}", message=f"edit {i}")

    with app.app_context():
        from models import Branch, Commit
        main = Branch.query.filter_by(document_id=doc["id"], is_main=True).first()
        main_commit_ids_after = [c.id for c in Commit.query.filter_by(branch_id=main.id).all()]

    assert main_commit_ids_before == main_commit_ids_after, (
        f"Main's commit list grew unexpectedly: "
        f"before={main_commit_ids_before} after={main_commit_ids_after}"
    )
    print("PASS: Main's commit list is unchanged by branch activity")


# --- runner -------------------------------------------------------------

if __name__ == "__main__":
    try:
        test_creating_branch_does_not_change_main()
        test_committing_on_branch_does_not_change_main()
        test_many_commits_on_branch_do_not_touch_main()
        test_sibling_branches_do_not_bleed_into_each_other()
        test_main_edits_after_fork_do_not_change_existing_branches()
        test_branch_of_branch_does_not_affect_either_ancestor()
        test_diff_endpoint_is_read_only()
        test_main_byte_for_byte_unchanged_across_full_branch_lifecycle()
        test_main_commit_count_is_unchanged_by_branch_activity()
        print("\nall branch-isolation tests passed!")
    finally:
        # clean up the temp db file so we don't leave clutter behind
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
            os.rmdir(_test_dir)
        except OSError:
            pass
