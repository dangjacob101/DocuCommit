import { useEffect, useState } from 'react'
import { listCommits } from '../api.js'
import { on, off } from '../events.js'

export default function CommitHistorySidebar({ branchId }) {
  const [commits, setCommits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setLoading(true)
      const rows = await listCommits(branchId)
      setCommits(rows.slice().reverse())
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
      <h3>History</h3>
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
              <span className="muted">#{c.id}</span>
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
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}
