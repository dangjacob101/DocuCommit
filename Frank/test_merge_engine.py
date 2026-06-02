"""Unit tests for the three-way merge engine."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from merge_engine import three_way_merge, apply_resolutions, validate_linear_progression, merge_summary


def test_both_unchanged():
    base = "line one\nline two\nline three\n"
    hunks = three_way_merge(base, base, base)
    kinds = [h["kind"] for h in hunks]
    assert all(k == "equal" for k in kinds), f"Expected all equal, got {kinds}"
    print("PASS: both_unchanged")


def test_only_main_changed():
    base = "line one\nline two\nline three\n"
    main = "line one\nline TWO\nline three\n"
    hunks = three_way_merge(base, main, base)
    auto_main = [h for h in hunks if h["kind"] == "auto-main"]
    assert len(auto_main) >= 1, f"Expected auto-main hunks, got {[h['kind'] for h in hunks]}"
    assert "TWO" in auto_main[0]["main"]
    print("PASS: only_main_changed")


def test_only_branch_changed():
    base = "line one\nline two\nline three\n"
    branch = "line one\nline BRANCH\nline three\n"
    hunks = three_way_merge(base, base, branch)
    auto_branch = [h for h in hunks if h["kind"] == "auto-branch"]
    assert len(auto_branch) >= 1, f"Expected auto-branch hunks, got {[h['kind'] for h in hunks]}"
    assert "BRANCH" in auto_branch[0]["branch"]
    print("PASS: only_branch_changed")


def test_non_overlapping_changes():
    base = "line one\nline two\nline three\nline four\nline five\n"
    main = "line one\nMAIN edit\nline three\nline four\nline five\n"
    branch = "line one\nline two\nline three\nline four\nBRANCH edit\n"
    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Expected no conflicts, got {len(conflicts)}: {conflicts}"
    auto_main = [h for h in hunks if h["kind"] == "auto-main"]
    auto_branch = [h for h in hunks if h["kind"] == "auto-branch"]
    assert len(auto_main) >= 1
    assert len(auto_branch) >= 1
    print("PASS: non_overlapping_changes")


def test_overlapping_changes_conflict():
    base = "line one\nline two\nline three\n"
    main = "line one\nMAIN version\nline three\n"
    branch = "line one\nBRANCH version\nline three\n"
    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) >= 1, f"Expected conflict, got {[h['kind'] for h in hunks]}"
    c = conflicts[0]
    assert "MAIN" in c["main"]
    assert "BRANCH" in c["branch"]
    print("PASS: overlapping_changes_conflict")


def test_same_change_both_sides():
    base = "line one\nline two\nline three\n"
    same = "line one\nline CHANGED\nline three\n"
    hunks = three_way_merge(base, same, same)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Identical changes should not conflict: {conflicts}"
    print("PASS: same_change_both_sides")


def test_apply_resolutions_pick_main():
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
    hunks = [
        {"id": "h0", "kind": "equal", "text": "start"},
        {"id": "h1", "kind": "conflict", "main": "Main text", "branch": "Branch text"},
        {"id": "h2", "kind": "equal", "text": "end"},
    ]
    result = apply_resolutions(hunks, {"h1": {"custom": "Custom merged"}})
    assert "Custom merged" in result
    print("PASS: apply_resolutions_custom")


def test_apply_resolutions_missing_raises():
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
    base = ""
    main = "Main added this\n"
    branch = "Branch added this\n"
    hunks = three_way_merge(base, main, branch)
    kinds = [h["kind"] for h in hunks]
    assert "conflict" in kinds or "auto-main" in kinds or "auto-branch" in kinds, \
        f"Expected changes, got {kinds}"
    print("PASS: empty_base")


def test_full_roundtrip():
    base = "The cat sat on the mat.\nIt was a sunny day.\nThe end.\n"
    main = "The cat sat on the mat.\nIt was a rainy day.\nThe end.\n"
    branch = "The dog sat on the mat.\nIt was a sunny day.\nThe end.\n"

    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    assert len(conflicts) == 0, f"Expected no conflicts for non-overlapping edits, got {conflicts}"

    merged = apply_resolutions(hunks, {})
    assert "dog" in merged, f"Expected 'dog' in merged text: {merged}"
    assert "rainy" in merged, f"Expected 'rainy' in merged text: {merged}"
    print("PASS: full_roundtrip")


def test_validate_linear_no_divergence():
    base = "hello\nworld\n"
    branch = "hello\nworld\nnew line\n"
    result = validate_linear_progression(base, base, branch)
    assert result["is_linear"] is True
    assert result["main_diverged"] is False
    assert result["auto_resolvable"] is True
    print("PASS: validate_linear_no_divergence")


def test_validate_linear_diverged_no_conflicts():
    base = "A\nB\nC\nD\nE\n"
    main = "A\nB-main\nC\nD\nE\n"
    branch = "A\nB\nC\nD\nE-branch\n"
    result = validate_linear_progression(base, main, branch)
    assert result["is_linear"] is False
    assert result["main_diverged"] is True
    assert result["has_conflicts"] is False
    assert result["auto_resolvable"] is True
    print("PASS: validate_linear_diverged_no_conflicts")


def test_validate_linear_diverged_with_conflicts():
    base = "A\nB\nC\n"
    main = "A\nB-main\nC\n"
    branch = "A\nB-branch\nC\n"
    result = validate_linear_progression(base, main, branch)
    assert result["is_linear"] is False
    assert result["has_conflicts"] is True
    assert result["conflict_count"] >= 1
    assert result["auto_resolvable"] is False
    print("PASS: validate_linear_diverged_with_conflicts")


def test_merge_summary_counts():
    base = "A\nB\nC\nD\nE\n"
    main = "A\nB-main\nC\nD\nE\n"
    branch = "A\nB\nC\nD\nE-branch\n"
    summary = merge_summary(base, main, branch)
    assert summary["total_hunks"] > 0
    assert summary["auto_main_hunks"] >= 1
    assert summary["auto_branch_hunks"] >= 1
    assert summary["conflict_hunks"] == 0
    assert summary["is_clean"] is True
    print("PASS: merge_summary_counts")


def test_reconstruct_span_preserves_unchanged_lines():
    base = "A\nB\nC\nD\nE\n"
    main = "A\nB-main\nC\nD-main\nE\n"
    branch = "A\nB-branch\nC\nD-branch\nE\n"
    hunks = three_way_merge(base, main, branch)
    conflicts = [h for h in hunks if h["kind"] == "conflict"]
    for c in conflicts:
        if "C" in c.get("main", "") or "C" in c.get("branch", ""):
            assert "C" in c["main"] and "C" in c["branch"], \
                "Unchanged line C should be preserved in conflict span"
    print("PASS: reconstruct_span_preserves_unchanged_lines")


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
    test_validate_linear_no_divergence()
    test_validate_linear_diverged_no_conflicts()
    test_validate_linear_diverged_with_conflicts()
    test_merge_summary_counts()
    test_reconstruct_span_preserves_unchanged_lines()
    print("\nAll merge engine tests passed!")

