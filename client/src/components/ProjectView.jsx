import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getProject, listBranches, updateDocument } from '../api.js'
import { slugify } from '../utils.js'

export default function ProjectView() {
  const { projectId } = useParams()
  const navigate = useNavigate()

  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [editingDocId, setEditingDocId] = useState(null)
  const [editTitleVal, setEditTitleVal] = useState('')
  const [savingTitle, setSavingTitle] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const data = await getProject(parseInt(projectId))
      setProject(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [projectId])

  async function openDocument(doc) {
    try {
      const branches = await listBranches(doc.id)
      const main = branches.find(b => b.name === 'Main') || branches[0]
      navigate(`/${slugify(project.name)}/${project.id}/${slugify(doc.title)}/${doc.id}/branches/${slugify(main.name)}`)
    } catch (e) {
      setError(e.message)
    }
  }

  async function saveDocTitle(id, original) {
    if (!editTitleVal.trim() || editTitleVal === original) {
      setEditingDocId(null)
      return
    }
    setSavingTitle(true)
    try {
      await updateDocument(id, editTitleVal)
      setProject({
        ...project,
        documents: project.documents.map(d =>
          d.id === id ? { ...d, title: editTitleVal } : d
        ),
      })
      setEditingDocId(null)
    } catch (e) {
      alert(`Rename failed: ${e.message}`)
    } finally {
      setSavingTitle(false)
    }
  }

  if (loading) return <p className="muted">Loading...</p>
  if (error) return (
    <div className="error error-row">
      <span>{error}</span>
      <div className="left-group">
        <button onClick={() => navigate('/')}>Back</button>
        <button onClick={load}>Retry</button>
      </div>
    </div>
  )

  return (
    <section>
      <div className="row">
        <div className="left-group">
          <button onClick={() => navigate('/')}>← Projects</button>
          <h2 style={{ margin: 0 }}>{project.name}</h2>
        </div>
        <button
          onClick={() => navigate(`/${slugify(project.name)}/${project.id}/new-document`)}
        >
          New Document
        </button>
      </div>

      {project.documents.length === 0 && (
        <p className="muted">No documents in this project yet. Create one to get started.</p>
      )}

      <ul className="doc-list">
        {project.documents.map((d) => (
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
                <button onClick={() => saveDocTitle(d.id, d.title)} disabled={savingTitle}>Save</button>
                <button onClick={() => setEditingDocId(null)} disabled={savingTitle}>Cancel</button>
              </div>
            ) : (
              <>
                <button className="link" onClick={() => openDocument(d)}>
                  {d.title}
                </button>
                <div className="doc-list-right">
                  <button
                    className="pencil-btn"
                    onClick={() => { setEditTitleVal(d.title); setEditingDocId(d.id) }}
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
