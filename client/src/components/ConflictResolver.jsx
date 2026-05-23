import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getMergePreview } from '../api.js'

function HunkEqual({ text }) {
  return (
    <div className="hunk hunk-equal">
      <div className="hunk-body">{text}</div>
    </div>
  )
}

function HunkAuto({ side, text }) {
  const label = side === 'main' ? 'Auto-accepted from Main' : 'Auto-accepted from branch'
  return (
    <div className={`hunk hunk-auto hunk-auto-${side}`}>
      <div className="hunk-tag">{label}</div>
      <div className="hunk-body">{text}</div>
    </div>
  )
}

function ConflictHunk({ hunk, resolution, editing, onPick, onStartEdit, onEditChange, onEditDone }) {
  if (editing) {
    return (
      <div className="hunk hunk-editing">
        <div className="hunk-resolved-head">
          <span className="hunk-tag">Editing manually</span>
        </div>
        <textarea
          className="hunk-edit"
          value={resolution.custom}
          onChange={(e) => onEditChange(e.target.value)}
          rows={4}
        />
        <div className="hunk-controls">
          <button onClick={onEditDone}>Done</button>
        </div>
      </div>
    )
  }

  if (resolution) {
    let label, content
    if (resolution === 'main') { label = 'Kept Main'; content = hunk.main }
    else if (resolution === 'branch') { label = 'Kept branch'; content = hunk.branch }
    else { label = 'Manual edit'; content = resolution.custom }
    return (
      <div className="hunk hunk-resolved">
        <div className="hunk-resolved-head">
          <span className="hunk-tag">{label}</span>
          <button className="link" onClick={() => onPick(null)}>Change</button>
        </div>
        <div className="hunk-body">{content}</div>
      </div>
    )
  }

  return (
    <div className="hunk hunk-conflict">
      <div className="hunk-cols">
        <div className="hunk-col">
          <div className="hunk-col-label">Main</div>
          <div className="hunk-body">{hunk.main}</div>
        </div>
        <div className="hunk-col">
          <div className="hunk-col-label">Branch</div>
          <div className="hunk-body">{hunk.branch}</div>
        </div>
      </div>
      <div className="hunk-controls">
        <button className="pill" onClick={() => onPick('main')}>Keep Main</button>
        <button className="pill" onClick={() => onPick('branch')}>Keep Branch</button>
        <button className="pill" onClick={onStartEdit}>Edit</button>
      </div>
    </div>
  )
}

export default function ConflictResolver() {
  const { docSlug, docId, branchName } = useParams()
  const navigate = useNavigate()

  const [preview, setPreview] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [editingId, setEditingId] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getMergePreview(parseInt(docId), branchName)
      .then((p) => {
        setPreview(p)
        const initial = {}
        for (const h of p.hunks) {
          if (h.kind === 'auto-main') initial[h.id] = 'main'
          if (h.kind === 'auto-branch') initial[h.id] = 'branch'
        }
        setResolutions(initial)
      })
      .catch((e) => setError(e.message))
  }, [docId, branchName])

  if (error) return <p className="error">{error}</p>
  if (!preview) return <p className="muted">Loading merge preview...</p>

  const conflicts = preview.hunks.filter(h => h.kind === 'conflict')
  const resolvedCount = conflicts.filter(h => {
    const r = resolutions[h.id]
    return r != null && editingId !== h.id
  }).length
  const allResolved = conflicts.length > 0 && resolvedCount === conflicts.length

  function setRes(id, value) {
    setResolutions(prev => {
      const next = { ...prev }
      if (value === null) delete next[id]
      else next[id] = value
      return next
    })
  }

  function pick(id, value) {
    if (editingId === id) setEditingId(null)
    setRes(id, value)
  }

  function startEdit(hunk) {
    setRes(hunk.id, { custom: hunk.branch })
    setEditingId(hunk.id)
  }

  function updateEdit(id, text) {
    setRes(id, { custom: text })
  }

  function finishEdit() {
    setEditingId(null)
  }

  const backPath = `/${docSlug}/${docId}/branches/${branchName}`

  function onFinish() {
    // still need real merge endpoints will add ltr
    alert(`Would submit ${conflicts.length} resolutions. (not implemented yet)`)
  }

  return (
    <section className="merge-page">
      <div className="row">
        <button onClick={() => navigate(backPath)}>← Back to Editor</button>
        <h2 className="diff-heading">
          Merge: <span className="diff-branch-name">{branchName}</span>
          <span className="diff-heading-sep"> into </span>
          <span className="diff-branch-name diff-branch-main">Main</span>
        </h2>
      </div>

      <div className="row">
        <span className="muted">
          {conflicts.length === 0
            ? 'No conflicts. Ready to merge.'
            : `${resolvedCount} of ${conflicts.length} conflicts resolved`}
        </span>
        <button onClick={onFinish} disabled={conflicts.length > 0 && !allResolved}>
          Finish merge
        </button>
      </div>

      <div className="merge-hunks">
        {preview.hunks.map(h => {
          if (h.kind === 'equal') return <HunkEqual key={h.id} text={h.text} />
          if (h.kind === 'auto-main') return <HunkAuto key={h.id} side="main" text={h.main} />
          if (h.kind === 'auto-branch') return <HunkAuto key={h.id} side="branch" text={h.branch} />
          return (
            <ConflictHunk
              key={h.id}
              hunk={h}
              resolution={resolutions[h.id] || null}
              editing={editingId === h.id}
              onPick={(v) => pick(h.id, v)}
              onStartEdit={() => startEdit(h)}
              onEditChange={(t) => updateEdit(h.id, t)}
              onEditDone={finishEdit}
            />
          )
        })}
      </div>
    </section>
  )
}
