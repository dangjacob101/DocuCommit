import sys
sys.path.insert(0, ".")

from diff_engine import make_diff, compute_edit_script, compute_visual_diff, EDIT_EQUAL, EDIT_DELETE, EDIT_INSERT
from utils import apply_patch

def test_identical():
    text = "hello\nworld\n"
    patch = make_diff(text, text)
    assert patch == "", f"Expected empty patch for identical text, got: {repr(patch)}"
    print("PASS: identical texts produce empty patch")

def test_simple_addition():
    old = "line one\nline two\n"
    new = "line one\nline added\nline two\n"
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, f"Expected {repr(new)}, got {repr(result)}"
    print("PASS: simple addition")

def test_simple_deletion():
    old = "line one\nline two\nline three\n"
    new = "line one\nline three\n"
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, f"Expected {repr(new)}, got {repr(result)}"
    print("PASS: simple deletion")

def test_modification():
    old = "line one\nline two\nline three\n"
    new = "line one\nline TWO\nline three\n"
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, f"Expected {repr(new)}, got {repr(result)}"
    print("PASS: modification")

def test_empty_to_content():
    old = ""
    new = "hello\nworld\n"
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    # apply_patch strips trailing newline when original had none
    assert result == "hello\nworld", f"Expected 'hello\\nworld', got {repr(result)}"
    print("PASS: empty to content")

def test_content_to_empty():
    old = "hello\nworld\n"
    new = ""
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new or result == "\n", f"Got {repr(result)}"
    print("PASS: content to empty")

def test_multi_hunk():
    old = "\n".join([f"line {i}" for i in range(20)]) + "\n"
    lines = old.splitlines(keepends=True)
    lines[2] = "CHANGED line 2\n"
    lines[15] = "CHANGED line 15\n"
    new = "".join(lines)
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, f"Multi-hunk failed.\nExpected:\n{new}\nGot:\n{result}"
    print("PASS: multi-hunk diff")

def test_roundtrip_chain():
    texts = [
        "First draft of the contract.\nPayment terms: net 30.\n",
        "First draft of the contract.\nPayment terms: net 60.\nLiability clause added.\n",
        "Second draft of the contract.\nPayment terms: net 60.\nLiability clause added.\nSignature block.\n",
        "Second draft of the contract.\nPayment terms: net 45.\nSignature block.\n",
    ]
    current = texts[0]
    patches = []
    for i in range(1, len(texts)):
        p = make_diff(current, texts[i])
        patches.append(p)
        current = texts[i]

    reconstructed = texts[0]
    for p in patches:
        reconstructed = apply_patch(reconstructed, p)
    assert reconstructed == texts[-1], f"Chain roundtrip failed.\nExpected:\n{texts[-1]}\nGot:\n{reconstructed}"
    print("PASS: roundtrip chain of 4 versions")

def test_visual_diff():
    old = "The quick brown fox\njumps over the lazy dog\n"
    new = "The slow brown fox\nruns over the lazy cat\n"
    result = compute_visual_diff(old, new)
    types = [r["type"] for r in result]
    assert "modify" in types, f"Expected modify ops, got {types}"
    print("PASS: visual diff produces modify ops")

def test_no_trailing_newline():
    old = "no newline at end"
    new = "no newline at end, but changed"
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, f"Expected {repr(new)}, got {repr(result)}"
    print("PASS: no trailing newline")

def test_large_file():
    old_lines = [f"Line number {i} of the document\n" for i in range(500)]
    new_lines = list(old_lines)
    new_lines[50] = "MODIFIED line 50\n"
    new_lines[250] = "MODIFIED line 250\n"
    new_lines.insert(400, "INSERTED new line\n")
    del new_lines[100]

    old = "".join(old_lines)
    new = "".join(new_lines)
    patch = make_diff(old, new)
    result = apply_patch(old, patch)
    assert result == new, "Large file diff roundtrip failed"
    print("PASS: large file (500 lines, 4 changes)")

def test_3way_merge_conflict():
    from diff_engine import compute_3way_merge
    base = "A\nB\nC\nD\n"
    main = "A\nX\nC\nD\n"
    branch = "A\nY\nC\nD\n"
    hunks = compute_3way_merge(base, main, branch)
    assert len(hunks) == 4
    assert hunks[0]["kind"] == "equal" and hunks[0]["text"] == "A\n"
    assert hunks[1]["kind"] == "conflict" and hunks[1]["main"] == "X\n" and hunks[1]["branch"] == "Y\n"
    print("PASS: 3-way merge conflict")

def test_3way_merge_auto_main():
    from diff_engine import compute_3way_merge
    base = "A\nB\nC\n"
    main = "A\nB_main\nC\n"
    branch = "A\nB\nC\n"
    hunks = compute_3way_merge(base, main, branch)
    assert len(hunks) == 3
    assert hunks[1]["kind"] == "auto-main" and hunks[1]["text"] == "B_main\n"
    print("PASS: 3-way merge auto-main")

def test_3way_merge_auto_branch():
    from diff_engine import compute_3way_merge
    base = "A\nB\nC\n"
    main = "A\nB\nC\n"
    branch = "A\nB_branch\nC\n"
    hunks = compute_3way_merge(base, main, branch)
    assert len(hunks) == 3
    assert hunks[1]["kind"] == "auto-branch" and hunks[1]["text"] == "B_branch\n"
    print("PASS: 3-way merge auto-branch")

def test_3way_merge_insert_conflict():
    from diff_engine import compute_3way_merge
    base = "A\n"
    main = "A\nB\n"
    branch = "A\nC\n"
    hunks = compute_3way_merge(base, main, branch)
    assert len(hunks) == 2
    assert hunks[1]["kind"] == "conflict" and hunks[1]["main"] == "B\n" and hunks[1]["branch"] == "C\n"
    print("PASS: 3-way merge insert conflict")

if __name__ == "__main__":
    test_identical()
    test_simple_addition()
    test_simple_deletion()
    test_modification()
    test_empty_to_content()
    test_content_to_empty()
    test_multi_hunk()
    test_roundtrip_chain()
    test_visual_diff()
    test_no_trailing_newline()
    test_large_file()
    test_3way_merge_conflict()
    test_3way_merge_auto_main()
    test_3way_merge_auto_branch()
    test_3way_merge_insert_conflict()
    print("\nAll tests passed!")
