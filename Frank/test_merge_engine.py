"""Unit tests for the three-way merge engine."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from merge_engine import three_way_merge, apply_resolutions


def test_both_unchanged():
    """When neither side changes the base, all hunks are equal."""
    base = "line one\nline two\nline three\n"
    hunks = three_way_merge(base, base, base)
    kinds = [h["kind"] for h in hunks]
    assert all(k == "equal" for k in kinds), f"Expected all equal, got {kinds}"
    print("PASS: both_unchanged")


def test_only_main_changed():
    """When only Main changes a line, hunk is auto-main."""
    base = "line one\nline two\nline three\n"
    main = "line one\nline TWO\nline three\n"
    hunks = three_way_merge(base, main, base)
    auto_main = [h for h in hunks if h["kind"] == "auto-main"]
    assert len(auto_main) >= 1, f"Expected auto-main hunks, got {[h['kind'] for h in hunks]}"
    assert "TWO" in auto_main[0]["main"]
    print("PASS: only_main_changed")


def test_only_branch_changed():
    """When only the branch changes a line, hunk is auto-branch."""
    base = "line one\nline two\nline three\n"
    branch = "line one\nline BRANCH\nline three\n"
    hunks = three_way_merge(base, base, branch)
    auto_branch = [h for h in hunks if h["kind"] == "auto-branch"]
    assert len(auto_branch) >= 1, f"Expected auto-branch hunks, got {[h['kind'] for h in hunks]}"
    assert "BRANCH" in auto_branch[0]["branch"]
    print("PASS: only_branch_changed")


def test_non_overlapping_changes():
    """When both sides change different lines, no conflicts."""
    base = "line one\nline two\nline three\nline four\nline five\n"
    main = "line one\nMAIN edit\nline three\nline four\nline five\n"
    branch = "line one\nline two\nline three\nline four\nBRANCH edit\n"
    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Expected no conflicts, got {len(conflicts)}: {conflicts}"
    auto_main = [h for h in hunks if h["kind"] == "auto-main"]
    auto_branch = [h for h in hunks if h["kind"] == "auto-branch"]
    assert len(auto_main) >= 1, "Expected at least one auto-main hunk"
    assert len(auto_branch) >= 1, "Expected at least one auto-branch hunk"
    print("PASS: non_overlapping_changes")


def test_overlapping_changes_conflict():
    """When both sides change the same line differently, it's a conflict."""
    base = "line one\nline two\nline three\n"
    main = "line one\nMAIN version\nline three\n"
    branch = "line one\nBRANCH version\nline three\n"
    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) >= 1, f"Expected conflict, got {[h['kind'] for h in hunks]}"
    c = conflicts[0]
    assert "MAIN" in c["main"], f"Expected MAIN in main side, got {c['main']}"
    assert "BRANCH" in c["branch"], f"Expected BRANCH in branch side, got {c['branch']}"
    print("PASS: overlapping_changes_conflict")


def test_same_change_both_sides():
    """When both sides make identical changes, it auto-resolves as equal."""
    base = "line one\nline two\nline three\n"
    same = "line one\nline CHANGED\nline three\n"
    hunks = three_way_merge(base, same, same)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Identical changes should not conflict: {conflicts}"
    print("PASS: same_change_both_sides")


def test_apply_resolutions_pick_main():
    """Resolving a conflict by picking Main."""
    hunks = [
        {"id": "h0", "kind": "equal", "text": "start"},
        {"id": "h1", "kind": "conflict", "main": "Main text", "branch": "Branch text"},
        {"id": "h2", "kind": "equal", "text": "end"},
    ]
    result = apply_resolutions(hunks, {"h1": "main"})
    assert "Main text" in result
    assert "Branch text" not in result
    print("PASS: apply_resolutions_pick_main")


def test_apply_resolutions_pick_branch():
    """Resolving a conflict by picking branch."""
    hunks = [
        {"id": "h0", "kind": "equal", "text": "start"},
        {"id": "h1", "kind": "conflict", "main": "Main text", "branch": "Branch text"},
        {"id": "h2", "kind": "equal", "text": "end"},
    ]
    result = apply_resolutions(hunks, {"h1": "branch"})
    assert "Branch text" in result
    assert "Main text" not in result
    print("PASS: apply_resolutions_pick_branch")


def test_apply_resolutions_custom():
    """Resolving a conflict with custom text."""
    hunks = [
        {"id": "h0", "kind": "equal", "text": "start"},
        {"id": "h1", "kind": "conflict", "main": "Main text", "branch": "Branch text"},
        {"id": "h2", "kind": "equal", "text": "end"},
    ]
    result = apply_resolutions(hunks, {"h1": {"custom": "Custom merged"}})
    assert "Custom merged" in result
    print("PASS: apply_resolutions_custom")


def test_apply_resolutions_missing_raises():
    """Missing resolution for a conflict raises ValueError."""
    hunks = [
        {"id": "h0", "kind": "conflict", "main": "A", "branch": "B"},
    ]
    try:
        apply_resolutions(hunks, {})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("PASS: apply_resolutions_missing_raises")


def test_auto_hunks_no_resolution_needed():
    """Auto-main and auto-branch hunks don't need resolutions."""
    hunks = [
        {"id": "h0", "kind": "equal", "text": "start"},
        {"id": "h1", "kind": "auto-main", "main": "Main only"},
        {"id": "h2", "kind": "auto-branch", "branch": "Branch only"},
        {"id": "h3", "kind": "equal", "text": "end"},
    ]
    result = apply_resolutions(hunks, {})
    assert "Main only" in result
    assert "Branch only" in result
    print("PASS: auto_hunks_no_resolution_needed")


def test_empty_base():
    """Merging when the base is empty."""
    base = ""
    main = "Main added this\n"
    branch = "Branch added this\n"
    hunks = three_way_merge(base, main, branch)
    # Both added different content — should be a conflict
    kinds = [h["kind"] for h in hunks]
    assert "conflict" in kinds or "auto-main" in kinds or "auto-branch" in kinds, \
        f"Expected changes, got {kinds}"
    print("PASS: empty_base")


def test_full_roundtrip():
    """End-to-end: diverged edits → preview → resolve → correct merged text."""
    base = "The cat sat on the mat.\nIt was a sunny day.\nThe end.\n"
    main = "The cat sat on the mat.\nIt was a rainy day.\nThe end.\n"
    branch = "The dog sat on the mat.\nIt was a sunny day.\nThe end.\n"

    hunks = three_way_merge(base, main, branch)

    # Should have auto-main (rainy), auto-branch (dog), and no conflicts
    # because the changes are on different lines
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Expected no conflicts for non-overlapping edits, got {conflicts}"

    merged = apply_resolutions(hunks, {})
    assert "dog" in merged, f"Expected 'dog' in merged text: {merged}"
    assert "rainy" in merged, f"Expected 'rainy' in merged text: {merged}"
    print("PASS: full_roundtrip")


if __name__ == "__main__":
    test_both_unchanged()
    test_only_main_changed()
    test_only_branch_changed()
    test_non_overlapping_changes()
    test_overlapping_changes_conflict()
    test_same_change_both_sides()
    test_apply_resolutions_pick_main()
    test_apply_resolutions_pick_branch()
    test_apply_resolutions_custom()
    test_apply_resolutions_missing_raises()
    test_auto_hunks_no_resolution_needed()
    test_empty_base()
    test_full_roundtrip()
    print("\nAll merge engine tests passed!")
