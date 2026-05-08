from typing import List, Tuple


EDIT_EQUAL = 0
EDIT_DELETE = 1
EDIT_INSERT = 2


def _hash_lines(a_lines: List[str], b_lines: List[str]) -> Tuple[List[int], List[int]]:
    """Maps lines to shared integer IDs so comparisons are O(1)."""
    table = {}
    next_id = 0

    def convert(lines):
        nonlocal next_id
        result = []
        for line in lines:
            lid = table.get(line)
            if lid is None:
                lid = next_id
                table[line] = lid
                next_id += 1
            result.append(lid)
        return result

    return convert(a_lines), convert(b_lines)


def _trim_common(a: List[int], b: List[int]) -> Tuple[int, int, List[int], List[int]]:
    """Strips matching prefix and suffix to shrink the edit graph."""
    prefix = 0
    limit = min(len(a), len(b))
    while prefix < limit and a[prefix] == b[prefix]:
        prefix += 1

    suffix = 0
    max_suffix = limit - prefix
    while suffix < max_suffix and a[-(suffix + 1)] == b[-(suffix + 1)]:
        suffix += 1

    a_mid = a[prefix:len(a) - suffix] if suffix else a[prefix:]
    b_mid = b[prefix:len(b) - suffix] if suffix else b[prefix:]
    return prefix, suffix, a_mid, b_mid


def _myers(a: List[int], b: List[int]) -> List[Tuple[int, int, int, int]]:
    """Myers O(ND) shortest-edit-script on the edit graph.

    Returns a list of (prev_x, prev_y, x, y) moves representing
    the path through the edit graph. Diagonal moves are matches,
    horizontal moves are deletes, vertical moves are inserts.
    """
    n, m = len(a), len(b)
    if n == 0 and m == 0:
        return []

    max_d = n + m
    v = {1: 0}
    history = []

    for d in range(max_d + 1):
        history.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, -1) + 1

            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            v[k] = x
            if x >= n and y >= m:
                return _backtrack(history, n, m, d, v)

    return _backtrack(history, n, m, max_d, v)


def _backtrack(history, n, m, final_d, final_v):
    """Walks backward through Myers snapshots to reconstruct the edit path."""
    x, y = n, m
    moves = []

    for d in range(final_d, 0, -1):
        v_prev = history[d]
        k = x - y

        if k == -d or (k != d and v_prev.get(k - 1, -1) < v_prev.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1

        prev_x = v_prev.get(prev_k, 0)
        prev_y = prev_x - prev_k

        while x > prev_x and y > prev_y:
            moves.append((x - 1, y - 1, x, y))
            x -= 1
            y -= 1

        moves.append((prev_x, prev_y, x, y))
        x, y = prev_x, prev_y

    while x > 0 and y > 0:
        moves.append((x - 1, y - 1, x, y))
        x -= 1
        y -= 1

    moves.reverse()
    return moves


def _moves_to_edits(moves, a_lines, b_lines, prefix):
    """Converts raw edit-graph moves into (op, content) pairs."""
    edits = []

    for px, py, cx, cy in moves:
        dx = cx - px
        dy = cy - py
        real_ax = px + prefix
        real_by = py + prefix

        if dx == 1 and dy == 1:
            edits.append((EDIT_EQUAL, a_lines[real_ax]))
        elif dx == 1 and dy == 0:
            edits.append((EDIT_DELETE, a_lines[real_ax]))
        elif dx == 0 and dy == 1:
            edits.append((EDIT_INSERT, b_lines[real_by]))

    return edits


def compute_edit_script(old_lines: List[str], new_lines: List[str]):
    """Produces an optimized edit script between two line lists.

    Returns list of (op, line_content) where op is EDIT_EQUAL/DELETE/INSERT.
    """
    if old_lines == new_lines:
        return [(EDIT_EQUAL, line) for line in old_lines]

    ha, hb = _hash_lines(old_lines, new_lines)

    prefix, suffix, a_mid, b_mid = _trim_common(ha, hb)

    edits = []

    for i in range(prefix):
        edits.append((EDIT_EQUAL, old_lines[i]))

    if not a_mid and not b_mid:
        pass
    elif not a_mid:
        for i in range(prefix, prefix + len(b_mid)):
            edits.append((EDIT_INSERT, new_lines[i]))
    elif not b_mid:
        for i in range(prefix, prefix + len(a_mid)):
            edits.append((EDIT_DELETE, old_lines[i]))
    else:
        moves = _myers(a_mid, b_mid)
        edits.extend(_moves_to_edits(moves, old_lines, new_lines, prefix))

    tail_start_a = len(old_lines) - suffix
    for i in range(tail_start_a, len(old_lines)):
        edits.append((EDIT_EQUAL, old_lines[i]))

    return edits


def _group_into_hunks(edits, context=3):
    """Groups edit operations into unified-diff hunks with surrounding context."""
    change_indices = [i for i, (op, _) in enumerate(edits) if op != EDIT_EQUAL]
    if not change_indices:
        return []

    hunks = []
    hunk_start = 0
    i = 0

    while i < len(change_indices):
        start = max(0, change_indices[i] - context)
        end = min(len(edits), change_indices[i] + context + 1)

        while i < len(change_indices) - 1 and change_indices[i + 1] <= end + context:
            i += 1
            end = min(len(edits), change_indices[i] + context + 1)

        hunks.append((start, end))
        i += 1

    return hunks


def format_unified_diff(old_lines, new_lines, edits, from_label="previous", to_label="current", context=3):
    """Formats edit script as a unified diff string compatible with apply_patch."""
    hunks = _group_into_hunks(edits, context)
    if not hunks:
        return ""

    output = []
    output.append(f"--- {from_label}\n")
    output.append(f"+++ {to_label}\n")

    for hunk_start, hunk_end in hunks:
        old_pos = 1
        new_pos = 1
        for i in range(hunk_start):
            op = edits[i][0]
            if op == EDIT_EQUAL or op == EDIT_DELETE:
                old_pos += 1
            if op == EDIT_EQUAL or op == EDIT_INSERT:
                new_pos += 1

        old_count = 0
        new_count = 0
        lines = []

        for i in range(hunk_start, hunk_end):
            op, content = edits[i]
            if not content.endswith("\n"):
                content += "\n"
            if op == EDIT_EQUAL:
                lines.append(" " + content)
                old_count += 1
                new_count += 1
            elif op == EDIT_DELETE:
                lines.append("-" + content)
                old_count += 1
            elif op == EDIT_INSERT:
                lines.append("+" + content)
                new_count += 1

        header = f"@@ -{old_pos},{old_count} +{new_pos},{new_count} @@\n"
        output.append(header)
        output.extend(lines)

    return "".join(output)


def make_diff(old_text: str, new_text: str) -> str:
    """Produces a unified diff patch from old_text to new_text."""
    def ensure_newline(t):
        if t and not t.endswith("\n"):
            return t + "\n"
        return t

    old_norm = ensure_newline(old_text)
    new_norm = ensure_newline(new_text)
    old_lines = old_norm.splitlines(keepends=True) if old_norm else []
    new_lines = new_norm.splitlines(keepends=True) if new_norm else []

    edits = compute_edit_script(old_lines, new_lines)
    return format_unified_diff(old_lines, new_lines, edits)


def compute_word_diff(old_text: str, new_text: str):
    """Word-level diff for visual highlighting in the frontend.

    Returns list of (op, word) pairs for rendering additions/deletions inline.
    """
    old_words = old_text.split() if old_text else []
    new_words = new_text.split() if new_text else []
    return compute_edit_script(old_words, new_words)


def compute_visual_diff(old_text: str, new_text: str):
    """Line-level diff with word-level detail for the visual comparison UI.

    Returns a list of dicts, each representing a line in the diff output:
      {"type": "equal"|"delete"|"insert"|"modify", "old": str, "new": str, "words": [...]}
    """
    old_lines = old_text.splitlines(keepends=True) if old_text else []
    new_lines = new_text.splitlines(keepends=True) if new_text else []
    edits = compute_edit_script(old_lines, new_lines)

    result = []
    i = 0
    while i < len(edits):
        op, content = edits[i]

        if op == EDIT_EQUAL:
            result.append({"type": "equal", "content": content.rstrip("\n")})
            i += 1

        elif op == EDIT_DELETE:
            deletes = []
            while i < len(edits) and edits[i][0] == EDIT_DELETE:
                deletes.append(edits[i][1].rstrip("\n"))
                i += 1
            inserts = []
            while i < len(edits) and edits[i][0] == EDIT_INSERT:
                inserts.append(edits[i][1].rstrip("\n"))
                i += 1

            if inserts:
                for j in range(max(len(deletes), len(inserts))):
                    old_line = deletes[j] if j < len(deletes) else ""
                    new_line = inserts[j] if j < len(inserts) else ""
                    words = compute_word_diff(old_line, new_line)
                    result.append({
                        "type": "modify",
                        "old": old_line,
                        "new": new_line,
                        "words": [(w[0], w[1]) for w in words],
                    })
            else:
                for line in deletes:
                    result.append({"type": "delete", "content": line})

        elif op == EDIT_INSERT:
            result.append({"type": "insert", "content": content.rstrip("\n")})
            i += 1

    return result
