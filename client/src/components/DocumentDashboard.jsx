import { useEffect, useState } from 'react'
import { listDocuments } from '../api.js'
import { emit, on, off } from '../events.js'

export default function DocumentDashboard({ onNew }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setLoading(true)
      const rows = await listDocuments()
      setDocs(rows)
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
    on('document-changed', refresh)
    return () => off('document-changed', refresh)
  }, [])

  return (
    <section>
      <div className="row">
        <h2>Documents</h2>
        <button onClick={onNew}>New Document</button>
      </div>
      {loading && <p className="muted">Loading...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && docs.length === 0 && (
        <p className="muted">No documents yet. Create one to get started.</p>
      )}
      <ul className="doc-list">
        {docs.map((d) => (
          <li key={d.id}>
            <button
              className="link"
              onClick={() => emit('open-document', d)}
            >
              {d.title}
            </button>
            <span className="muted">{formatDate(d.updated_at)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}
