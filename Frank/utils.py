import json as _json
import re as _re

from diff_engine import make_diff, compute_visual_diff  # noqa: F401


def extract_plain_text(content: str) -> str:
    """Extract human-readable plain text from a TipTap JSON string or raw HTML.

    TipTap stores documents as ProseMirror JSON.  We walk the node tree and
    concatenate text leaves, inserting newlines at block boundaries so the
    Myers diff algorithm sees prose lines rather than serialized JSON tokens.

    Falls back to a simple HTML-tag strip for legacy HTML content.

    All extracted lines are normalized before being returned:
      - surrounding whitespace is stripped
      - internal runs of whitespace are collapsed to a single space
      - blank lines are dropped
    This ensures invisible differences (trailing spaces, mixed whitespace from
    HTML vs JSON paths) never show up as false-positive modifications.
    """
    if not content:
        return ""

    try:
        doc = _json.loads(content)
        lines = []
        _collect_text(doc, lines)
        raw_lines = lines
    except (ValueError, TypeError):
        # Not JSON — strip HTML tags for legacy content
        text = _re.sub(r"<[^>]+>", "\n", content)
        raw_lines = text.splitlines()

    normalized = []
    for line in raw_lines:
        # Strip surrounding whitespace, then collapse internal runs
        clean = _re.sub(r"\s+", " ", line).strip()
        if clean:
            normalized.append(clean)

    return "\n".join(normalized)


# Block-level node types that should be rendered as separate lines.
_BLOCK_NODES = {
    "paragraph", "heading", "blockquote", "codeBlock",
    "bulletList", "orderedList", "listItem",
    "horizontalRule", "hardBreak",
}


def _collect_text(node, lines, _current=None):
    """Recursively walk a ProseMirror node tree, filling *lines*."""
    if not isinstance(node, dict):
        return

    node_type = node.get("type", "")

    if node_type == "text":
        text = node.get("text", "")
        if _current is not None:
            _current.append(text)
        else:
            lines.append(text)
        return

    is_block = node_type in _BLOCK_NODES

    if is_block:
        buf = []
        for child in node.get("content") or []:
            _collect_text(child, lines, buf)
        line = "".join(buf).strip()
        if line:
            lines.append(line)
    else:
        # Inline / doc / unknown — keep accumulating into parent buffer
        for child in node.get("content") or []:
            _collect_text(child, lines, _current)


def _ensure_trailing_newline(text: str) -> str:
    if text and not text.endswith("\n"):
        return text + "\n"
    return text


def apply_patch(text: str, patch: str) -> str:
    """Apply a unified diff patch to text, returning the new version.

    This is a minimal implementation that handles the subset of unified diffs
    produced by make_diff (standard Python difflib output).
    """
    if not patch:
        return text

    normalized = _ensure_trailing_newline(text) if text else ""
    lines = normalized.splitlines(keepends=True)

    result = []
    source_idx = 0
    patch_lines = patch.splitlines(keepends=True)
    i = 0

    while i < len(patch_lines):
        line = patch_lines[i]

        if line.startswith("@@"):
            parts = line.split()
            old_range = parts[1]
            old_start = int(old_range.split(",")[0].lstrip("-"))
            old_start_idx = old_start - 1 if old_start > 0 else 0

            while source_idx < old_start_idx:
                result.append(lines[source_idx])
                source_idx += 1

            i += 1
            while i < len(patch_lines):
                pline = patch_lines[i]
                if pline.startswith("@@"):
                    break
                if pline.startswith("---") or pline.startswith("+++"):
                    i += 1
                    continue
                if pline.startswith("-"):
                    source_idx += 1
                elif pline.startswith("+"):
                    result.append(pline[1:])
                elif pline.startswith(" "):
                    result.append(pline[1:])
                    source_idx += 1
                i += 1
        else:
            i += 1

    while source_idx < len(lines):
        result.append(lines[source_idx])
        source_idx += 1

    output = "".join(result)
    # Strip the trailing newline we added for normalization
    if output.endswith("\n") and not text.endswith("\n"):
        output = output[:-1]
    return output


def reconstruct_content(commits) -> str:
    """Replay a sequence of commits (in order) to reconstruct the current text."""
    text = ""
    for commit in commits:
        text = apply_patch(text, commit.diff_patch)
    return text


def reconstruct_branch_content(branch) -> str:
    """Reconstruct the full text content of a branch by replaying its commits.

    For a Main branch: replay all commits from empty string.
    For a feature branch: reconstruct up to branched_from_commit_id on Main,
    then replay this branch's commits.
    """
    if branch.is_main:
        return reconstruct_content(branch.commits)

    # Feature branch: start from the snapshot point on Main
    from models import Commit, Branch

    main_branch = Branch.query.filter_by(
        document_id=branch.document_id, is_main=True
    ).first()

    if main_branch is None:
        return reconstruct_content(branch.commits)

    if branch.branched_from_commit_id is not None:
        base_commits = Commit.query.filter(
            Commit.branch_id == main_branch.id,
            Commit.id <= branch.branched_from_commit_id,
        ).order_by(Commit.id).all()
    else:
        base_commits = main_branch.commits

    base_text = reconstruct_content(base_commits)
    text = base_text
    for commit in branch.commits:
        text = apply_patch(text, commit.diff_patch)
    return text
