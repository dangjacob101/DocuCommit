import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { listBranches, diffBranch } from '../api.js'
import { slugify } from '../utils.js'

// ─── Word-level inline highlight ───────────────────────────────────────────

function WordSpan({ op, word }) {
  if (op === 0) return <span>{word} </span>
  if (op === 1) return <span className="diff-word-del">{word} </span>
  if (op === 2) return <span className="diff-word-ins">{word} </span>
  return null
}

function ModifyRow({ row }) {
  return (
    <tr className="diff-row diff-row-modify">
      <td className="diff-line diff-line-old">
        {row.words.map(([op, word], i) =>
          op !== 2 ? <WordSpan key={i} op={op} word={word} /> : null
        )}
      </td>
      <td className="diff-line diff-line-new">
        {row.words.map(([op, word], i) =>
          op !== 1 ? <WordSpan key={i} op={op} word={word} /> : null
        )}
      </td>
    </tr>
  )
}

function DiffTable({ visualDiff }) {
  if (!visualDiff || visualDiff.length === 0) {
    return (
      <div className="diff-empty">
        <span className="diff-empty-icon">✓</span>
        <p>No differences — this branch is identical to Main.</p>
      </div>
    )
  }

  return (
    <table className="diff-table">
      <thead>
        <tr>
          <th className="diff-th">Main</th>
          <th className="diff-th">This Branch</th>
        </tr>
      </thead>
      <tbody>
        {visualDiff.map((row, i) => {
          if (row.type === 'equal') {
            return (
              <tr key={i} className="diff-row diff-row-equal">
                <td className="diff-line">{row.content}</td>
                <td className="diff-line">{row.content}</td>
              </tr>
            )
          }
          if (row.type === 'insert') {
            return (
              <tr key={i} className="diff-row diff-row-ins">
                <td className="diff-line diff-line-empty"></td>
                <td className="diff-line diff-line-new">{row.content}</td>
              </tr>
            )
          }
          if (row.type === 'delete') {
            return (
              <tr key={i} className="diff-row diff-row-del">
                <td className="diff-line diff-line-old">{row.content}</td>
                <td className="diff-line diff-line-empty"></td>
              </tr>
            )
          }
          if (row.type === 'modify') {
            return <ModifyRow key={i} row={row} />
          }
          return null
        })}
      </tbody>
    </table>
  )
}

// ─── Summary bar ───────────────────────────────────────────────────────────

function SummaryBar({ summary }) {
  return (
    <div className="diff-summary">
      <span className="diff-badge diff-badge-ins">+{summary.added} added</span>
      <span className="diff-badge diff-badge-del">−{summary.removed} removed</span>
      <span className="diff-badge diff-badge-mod">~{summary.modified} modified</span>
      <span className="diff-badge diff-badge-eq">{summary.unchanged} unchanged</span>
    </div>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────

export default function DiffViewer() {
  const { projectSlug, projectId, docId, docSlug, branchName } = useParams()
  const navigate = useNavigate()

  const [diffData, setDiffData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ignoreWs, setIgnoreWs] = useState(false)
  const [branchId, setBranchId] = useState(null)

  // Resolve branch ID once on mount or when branchName changes
  useEffect(() => {
    setBranchId(null)
    listBranches(parseInt(docId))
      .then((branches) => {
        const branch = branches.find((b) => slugify(b.name) === branchName)
        if (!branch) throw new Error(`Branch "${branchName}" not found`)
        setBranchId(branch.id)
      })
      .catch((e) => setError(e.message))
  }, [docId, branchName])

  // Fetch diff whenever branchId or ignoreWs changes
  useEffect(() => {
    if (branchId === null) return
    setLoading(true)
    setError(null)

    diffBranch(branchId, ignoreWs)
      .then(setDiffData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [branchId, ignoreWs])

  const backPath = `/${projectSlug}/${projectId}/${docSlug}/${docId}/branches/${branchName}`

  return (
    <section className="diff-page">
      <div className="row">
        <button onClick={() => navigate(backPath)}>← Back to Editor</button>
        <h2 className="diff-heading">
          Compare: <span className="diff-branch-name">{branchName}</span>
          <span className="diff-heading-sep"> vs </span>
          <span className="diff-branch-name diff-branch-main">Main</span>
        </h2>
      </div>

      <div className="row">
        <SummaryBar summary={diffData ? diffData.summary : { added: 0, removed: 0, modified: 0, unchanged: 0 }} />
        <button
          className={`ws-toggle${ignoreWs ? ' active' : ''}`}
          onClick={() => setIgnoreWs(!ignoreWs)}
          title="Hide changes where only whitespace differs"
        >
          {ignoreWs ? '◉ Ignoring whitespace' : '○ Show whitespace changes'}
        </button>
      </div>

      {loading && <p className="muted">Computing diff…</p>}
      {error && <p className="error">{error}</p>}

      {diffData && <DiffTable visualDiff={diffData.visual_diff} />}
    </section>
  )
}
