"""Three-way merge engine for DocuCommit — free of Flask/SQLAlchemy dependencies."""

from typing import List, Dict, Any, Tuple

from diff_engine import compute_edit_script, EDIT_EQUAL, EDIT_DELETE, EDIT_INSERT

def _edits_to_regions(edits):
    """Convert an edit script into contiguous regions of equal or changed lines."""
    regions = []
    base_idx = 0
    i = 0

    while i < len(edits):
        op, content = edits[i]

        if op == EDIT_EQUAL:
            base_start = base_idx
            base_lines = []
            while i < len(edits) and edits[i][0] == EDIT_EQUAL:
                base_lines.append(edits[i][1])
                base_idx += 1
                i += 1
            regions.append({
                "base_start": base_start,
                "base_end": base_idx,
                "kind": "equal",
                "base_lines": base_lines,
                "new_lines": list(base_lines),
            })
        else:
            base_start = base_idx
            base_lines = []
            new_lines = []
            while i < len(edits) and edits[i][0] != EDIT_EQUAL:
                eop, econtent = edits[i]
                if eop == EDIT_DELETE:
                    base_lines.append(econtent)
                    base_idx += 1
                elif eop == EDIT_INSERT:
                    new_lines.append(econtent)
                i += 1
            regions.append({
                "base_start": base_start,
                "base_end": base_idx,
                "kind": "changed",
                "base_lines": base_lines,
                "new_lines": new_lines,
            })

    return regions


def three_way_merge(
    base_text: str, main_text: str, branch_text: str
) -> List[Dict[str, Any]]:
    """Perform a three-way merge and return a list of classified hunks."""
    base_lines = base_text.splitlines(keepends=True) if base_text else []
    main_lines = main_text.splitlines(keepends=True) if main_text else []
    branch_lines = branch_text.splitlines(keepends=True) if branch_text else []

    main_edits = compute_edit_script(base_lines, main_lines)
    branch_edits = compute_edit_script(base_lines, branch_lines)

    main_regions = _edits_to_regions(main_edits)
    branch_regions = _edits_to_regions(branch_edits)

    main_change_map = _build_change_map(main_regions)
    branch_change_map = _build_change_map(branch_regions)

    hunks = []
    hunk_id = 0
    base_len = len(base_lines)
    base_idx = 0
    emitted_regions = set()

    while base_idx < base_len:
        m_region = main_change_map.get(base_idx)
        if m_region and id(m_region) in emitted_regions:
            m_region = None

        b_region = branch_change_map.get(base_idx)
        if b_region and id(b_region) in emitted_regions:
            b_region = None

        if m_region is not None and b_region is not None:
            m_new, b_new, region_end, visited_main, visited_branch = _collect_overlapping(
                base_idx, main_change_map, branch_change_map,
                base_len, base_lines,
            )
            emitted_regions.update(visited_main)
            emitted_regions.update(visited_branch)

            m_text = "".join(m_new).rstrip("\n")
            b_text = "".join(b_new).rstrip("\n")

            if m_text == b_text:
                hunks.append({
                    "id": f"h{hunk_id}",
                    "kind": "equal",
                    "text": m_text,
                })
            else:
                hunks.append({
                    "id": f"h{hunk_id}",
                    "kind": "conflict",
                    "main": m_text,
                    "branch": b_text,
                })
            hunk_id += 1
            base_idx = region_end

        elif m_region is not None:
            m_text = "".join(m_region["new_lines"]).rstrip("\n")
            hunks.append({
                "id": f"h{hunk_id}",
                "kind": "auto-main",
                "main": m_text,
            })
            hunk_id += 1
            emitted_regions.add(id(m_region))
            base_idx = m_region["base_end"]

        elif b_region is not None:
            b_text = "".join(b_region["new_lines"]).rstrip("\n")
            hunks.append({
                "id": f"h{hunk_id}",
                "kind": "auto-branch",
                "branch": b_text,
            })
            hunk_id += 1
            emitted_regions.add(id(b_region))
            base_idx = b_region["base_end"]

        else:
            equal_start = base_idx
            while (
                base_idx < base_len
                and (base_idx not in main_change_map or id(main_change_map[base_idx]) in emitted_regions)
                and (base_idx not in branch_change_map or id(branch_change_map[base_idx]) in emitted_regions)
            ):
                base_idx += 1
            text = "".join(base_lines[equal_start:base_idx]).rstrip("\n")
            hunks.append({
                "id": f"h{hunk_id}",
                "kind": "equal",
                "text": text,
            })
            hunk_id += 1

    _append_trailing_inserts(
        hunks, hunk_id, main_regions, branch_regions, base_len
    )

    return hunks


def _build_change_map(regions):
    """Map each base-line index to its changed region."""
    change_map = {}
    for region in regions:
        if region["kind"] == "changed":
            if region["base_start"] == region["base_end"]:
                change_map[region["base_start"]] = region
            else:
                for idx in range(region["base_start"], region["base_end"]):
                    change_map[idx] = region
    return change_map


def _collect_overlapping(start_idx, main_map, branch_map, base_len, base_lines):
    """Collect new-lines from overlapping change regions on both sides."""
    idx = start_idx
    end = start_idx
    visited_main = set()
    visited_branch = set()

    while idx < base_len and (idx == start_idx or idx < end):
        m = main_map.get(idx)
        b = branch_map.get(idx)

        if m is not None and id(m) not in visited_main:
            visited_main.add(id(m))
            end = max(end, m["base_end"])
        if b is not None and id(b) not in visited_branch:
            visited_branch.add(id(b))
            end = max(end, b["base_end"])

        if m is None and b is None and idx >= end:
            break
        idx += 1

    main_new = _reconstruct_span(start_idx, end, main_map, base_lines)
    branch_new = _reconstruct_span(start_idx, end, branch_map, base_lines)

    return main_new, branch_new, end, visited_main, visited_branch


def _reconstruct_span(start, end, change_map, base_lines):
    """Rebuild the new-side text for a span, preserving unchanged base lines."""
    if start == end:
        region = change_map.get(start)
        if region is not None:
            return list(region["new_lines"])
        return []

    result = []
    idx = start
    emitted_regions = set()

    while idx < end:
        region = change_map.get(idx)
        if region is not None and id(region) not in emitted_regions:
            emitted_regions.add(id(region))
            result.extend(region["new_lines"])
            idx = region["base_end"]
        else:
            result.append(base_lines[idx])
            idx += 1

    return result


def _append_trailing_inserts(hunks, hunk_id, main_regions, branch_regions, base_len):
    """Handle inserts added past the end of the base document."""
    main_trailing = []
    branch_trailing = []

    for r in main_regions:
        if r["kind"] == "changed" and r["base_start"] >= base_len and r["base_start"] == r["base_end"]:
            main_trailing.extend(r["new_lines"])

    for r in branch_regions:
        if r["kind"] == "changed" and r["base_start"] >= base_len and r["base_start"] == r["base_end"]:
            branch_trailing.extend(r["new_lines"])

    if not main_trailing and not branch_trailing:
        return

    m_text = "".join(main_trailing).rstrip("\n")
    b_text = "".join(branch_trailing).rstrip("\n")

    if main_trailing and branch_trailing:
        if m_text == b_text:
            hunks.append({"id": f"h{hunk_id}", "kind": "equal", "text": m_text})
        else:
            hunks.append({
                "id": f"h{hunk_id}",
                "kind": "conflict",
                "main": m_text,
                "branch": b_text,
            })
    elif main_trailing:
        hunks.append({"id": f"h{hunk_id}", "kind": "auto-main", "main": m_text})
    else:
        hunks.append({"id": f"h{hunk_id}", "kind": "auto-branch", "branch": b_text})


def apply_resolutions(
    hunks: List[Dict[str, Any]],
    resolutions: Dict[str, Any],
) -> str:
    """Produce final merged text by applying user resolutions to conflict hunks."""
    parts = []

    for hunk in hunks:
        kind = hunk["kind"]

        if kind == "equal":
            parts.append(hunk["text"])
        elif kind == "auto-main":
            parts.append(hunk["main"])
        elif kind == "auto-branch":
            parts.append(hunk["branch"])
        elif kind == "conflict":
            res = resolutions.get(hunk["id"])
            if res is None:
                raise ValueError(f"Missing resolution for conflict hunk {hunk['id']}")
            if res == "main":
                parts.append(hunk["main"])
            elif res == "branch":
                parts.append(hunk["branch"])
            elif isinstance(res, dict) and "custom" in res:
                if not isinstance(res["custom"], str):
                    raise ValueError(
                        f"Custom resolution for hunk {hunk['id']} must be a string"
                    )
                parts.append(res["custom"])
            else:
                raise ValueError(
                    f"Invalid resolution for hunk {hunk['id']}: {res!r}"
                )

    return "\n".join(parts)


def validate_linear_progression(
    base_text: str, main_text: str, branch_text: str
) -> Dict[str, Any]:
    """Check whether a branch→main merge is a clean fast-forward or has conflicts."""
    main_diverged = (base_text != main_text)

    if not main_diverged:
        return {
            "is_linear": True,
            "main_diverged": False,
            "has_conflicts": False,
            "conflict_count": 0,
            "auto_resolvable": True,
        }

    hunks = three_way_merge(base_text, main_text, branch_text)
    conflict_hunks = [h for h in hunks if h["kind"] == "conflict"]

    return {
        "is_linear": False,
        "main_diverged": True,
        "has_conflicts": len(conflict_hunks) > 0,
        "conflict_count": len(conflict_hunks),
        "auto_resolvable": len(conflict_hunks) == 0,
    }


def merge_summary(
    base_text: str, main_text: str, branch_text: str
) -> Dict[str, Any]:
    """Compute merge statistics without performing the merge."""
    hunks = three_way_merge(base_text, main_text, branch_text)

    counts = {"equal": 0, "auto-main": 0, "auto-branch": 0, "conflict": 0}
    for h in hunks:
        counts[h["kind"]] = counts.get(h["kind"], 0) + 1

    return {
        "total_hunks": len(hunks),
        "equal_hunks": counts["equal"],
        "auto_main_hunks": counts["auto-main"],
        "auto_branch_hunks": counts["auto-branch"],
        "conflict_hunks": counts["conflict"],
        "is_clean": counts["conflict"] == 0,
    }
