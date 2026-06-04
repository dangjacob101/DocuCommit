import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { listCommits } from '../api.js'
import { on, off } from '../events.js'


export default function CommitHistorySidebar({ branchId }) {
  const [commits, setCommits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  const { projectSlug, projectId, docSlug, docId, branchName } = useParams()


  async function load() {
    try {
      setLoading(true)
      const rows = await listCommits(branchId)
      const indexedRows = rows.map((c, idx) => ({
        ...c,
        seqNumber: idx + 1
      }))
      setCommits(indexedRows.reverse())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const refresh = () => load()
    on('commit-created', refresh)
    return () => off('commit-created', refresh)
  }, [branchId])

  return (
    <aside className="commit-history">
      <div className="commit-history-header">
        <h3>History</h3>
        <button
          id="view-full-history-btn"
          className="link history-full-link"
          onClick={() =>
            navigate(`/${projectSlug}/${projectId}/${docSlug}/${docId}/history/${branchName}`)
          }
        >
          View all →
        </button>
      </div>
      {loading && <p className="muted">Loading...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && commits.length === 0 && (
        <p className="muted">No commits yet.</p>
      )}
      <ul className="commit-list">
        {commits.map((c) => (
          <li key={c.id} className="commit-item">
            <div className="commit-message">{c.message}</div>
            <div className="commit-meta">
              <span className="muted">#{c.seqNumber}</span>
              <span className="muted">{formatDate(c.created_at)}</span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
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
