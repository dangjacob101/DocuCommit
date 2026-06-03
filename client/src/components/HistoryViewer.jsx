import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { listDocumentCommits } from '../api.js'
import { slugify } from '../utils.js'

// ─── Patch renderer ────────────────────────────────────────────────────────

function PatchPreview({ commit }) {
  if (!commit) {
    return (
      <div className="history-preview-empty">
        <span className="history-preview-icon">⏱</span>
        <p>Select a commit from the timeline to view its changes.</p>
      </div>
    )
  }

  // Use plain_text_patch (human-readable) when available.
  // Fall back to diff_patch for legacy commits that predate this field.
  const patch = commit.plain_text_patch || commit.diff_patch || ''
  const lines = patch.split('\n')

  return (
    <div className="history-preview-content">
      <div className="history-preview-header">
        <div className="history-preview-meta">
          <span className="history-branch-badge" data-main={commit.branch_is_main}>
            {commit.branch_name}
          </span>
          <span className="history-preview-title">{commit.message}</span>
        </div>
        <span className="history-preview-date">{formatDate(commit.created_at)}</span>
      </div>

      <div className="history-patch">
        {lines.map((line, i) => {
          if (line.startsWith('+') && !line.startsWith('+++')) {
            return <div key={i} className="history-patch-add">{line}</div>
          }
          if (line.startsWith('-') && !line.startsWith('---')) {
            return <div key={i} className="history-patch-del">{line}</div>
          }
          if (line.startsWith('@@')) {
            return <div key={i} className="history-patch-hunk">{line}</div>
          }
          return <div key={i} className="history-patch-ctx">{line || '\u00A0'}</div>
        })}
      </div>
    </div>
  )
}

// ─── Timeline entry ─────────────────────────────────────────────────────────

function CommitEntry({ commit, isSelected, onClick }) {
  return (
    <button
      className={`history-entry${isSelected ? ' history-entry-selected' : ''}`}
      onClick={onClick}
      id={`commit-entry-${commit.id}`}
    >
      <div className="history-entry-top">
        <span className="history-branch-badge" data-main={commit.branch_is_main}>
          {commit.branch_name}
        </span>
        <span className="history-entry-num">#{commit.seq}</span>
      </div>
      <div className="history-entry-message">{commit.message}</div>
      <div className="history-entry-date">{formatDate(commit.created_at)}</div>
    </button>
  )
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function HistoryViewer() {
  const { projectSlug, projectId, docSlug, docId, branchName } = useParams()
  const navigate = useNavigate()

  const [commits, setCommits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  const backPath = `/${projectSlug}/${projectId}/${docSlug}/${docId}/branches/${branchName}`

  useEffect(() => {
    setLoading(true)
    listDocumentCommits(parseInt(docId))
      .then((rows) => {
        // Assign per-branch sequential numbers
        const seqByBranch = {}
        const enriched = rows.map((c) => {
          seqByBranch[c.branch_id] = (seqByBranch[c.branch_id] || 0) + 1
          return { ...c, seq: seqByBranch[c.branch_id] }
        })
        // Newest first
        setCommits(enriched.reverse())
        setError(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId])

  return (
    <section className="history-page">
      {/* ── Top bar ── */}
      <div className="row history-topbar">
        <button id="history-back-btn" onClick={() => navigate(backPath)}>
          ← Back to Editor
        </button>
        <h2 className="history-heading">
          Commit History
          {!loading && !error && (
            <span className="history-count">{commits.length} commit{commits.length !== 1 ? 's' : ''}</span>
          )}
        </h2>
      </div>

      {loading && <p className="muted">Loading history…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && commits.length === 0 && (
        <div className="history-empty">
          <span className="history-preview-icon">📄</span>
          <p>No commits yet on this document.</p>
        </div>
      )}

      {!loading && !error && commits.length > 0 && (
        <div className="history-layout">
          {/* ── Timeline ── */}
          <aside className="history-timeline">
            {commits.map((c) => (
              <CommitEntry
                key={c.id}
                commit={c}
                isSelected={selected?.id === c.id}
                onClick={() => setSelected(c)}
              />
            ))}
          </aside>

          {/* ── Patch preview ── */}
          <div className="history-preview">
            <PatchPreview commit={selected} />
          </div>
        </div>
      )}
    </section>
  )
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    const utcIso = iso.endsWith('Z') ? iso : iso + 'Z'
    return new Date(utcIso).toLocaleString()
  } catch {
    return iso
  }
}
