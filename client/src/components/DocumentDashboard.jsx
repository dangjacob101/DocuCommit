import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listDocuments, listBranches } from '../api.js'
import { slugify } from '../utils.js'

export default function DocumentDashboard() {
  const navigate = useNavigate()
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
  }, [])

  async function openDocument(doc) {
    try {
      const branches = await listBranches(doc.id)
      const main = branches.find(b => b.name === 'Main') || branches[0]
      navigate(`/${slugify(doc.title)}/${doc.id}/branches/${slugify(main.name)}`)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <section>
      <div className="row">
        <h2>Documents</h2>
        <button onClick={() => navigate('/create-new-document')}>New Document</button>
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
              onClick={() => openDocument(d)}
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
