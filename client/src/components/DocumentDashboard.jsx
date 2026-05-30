import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listDocuments, listBranches, updateDocument } from '../api.js'
import { slugify } from '../utils.js'

export default function DocumentDashboard() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [editingDocId, setEditingDocId] = useState(null)
  const [editTitleVal, setEditTitleVal] = useState('')
  const [savingTitle, setSavingTitle] = useState(false)

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

  async function handleSaveTitle(id, originalTitle) {
    if (!editTitleVal.trim() || editTitleVal === originalTitle) {
      setEditingDocId(null)
      return
    }
    setSavingTitle(true)
    try {
      await updateDocument(id, editTitleVal)
      setDocs(docs.map(d => d.id === id ? { ...d, title: editTitleVal } : d))
      setEditingDocId(null)
    } catch (e) {
      alert(`Failed to update title: ${e.message}`)
    } finally {
      setSavingTitle(false)
    }
  }

  return (
    <section>
      <div className="row">
        <h2>Documents</h2>
        <button onClick={() => navigate('/create-new-document')}>New Document</button>
      </div>
      {loading && <p className="muted">Loading...</p>}
      {error && (
        <div className="error error-row">
          <span>{error}</span>
          <button onClick={load}>Retry</button>
        </div>
      )}
      {!loading && !error && docs.length === 0 && (
        <p className="muted">No documents yet. Create one to get started.</p>
      )}
      <ul className="doc-list">
        {docs.map((d) => (
          <li key={d.id}>
            {editingDocId === d.id ? (
              <div className="title-edit-group dashboard-edit">
                <input 
                  className="title-edit-input" 
                  value={editTitleVal} 
                  onChange={e => setEditTitleVal(e.target.value)} 
                  disabled={savingTitle}
                  autoFocus 
                />
                <button onClick={() => handleSaveTitle(d.id, d.title)} disabled={savingTitle}>Save</button>
                <button onClick={() => setEditingDocId(null)} disabled={savingTitle}>Cancel</button>
              </div>
            ) : (
              <>
                <button
                  className="link"
                  onClick={() => openDocument(d)}
                >
                  {d.title}
                </button>
                <div className="doc-list-right">
                  <span className="muted">{formatDate(d.updated_at)}</span>
                  <button 
                    className="pencil-btn" 
                    onClick={() => {
                      setEditTitleVal(d.title)
                      setEditingDocId(d.id)
                    }}
                    title="Rename document"
                  >
                    ✎
                  </button>
                </div>
              </>
            )}
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
