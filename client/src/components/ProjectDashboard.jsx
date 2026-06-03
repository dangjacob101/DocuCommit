import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProjects, createProject, renameProject, deleteProject } from '../api.js'
import { slugify } from '../utils.js'
import Modal from './Modal.jsx'

export default function ProjectDashboard() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  async function load() {
    try {
      setLoading(true)
      const rows = await listProjects()
      setProjects(rows)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openProject(p) {
    navigate(`/${slugify(p.name)}/${p.id}`)
  }

  async function submitNew(e) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    try {
      const proj = await createProject(newName.trim())
      setProjects([...projects, proj])
      setNewName('')
      setShowNew(false)
      navigate(`/${slugify(proj.name)}/${proj.id}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  async function saveRename(id, original) {
    if (!editName.trim() || editName === original) {
      setEditingId(null)
      return
    }
    setSavingEdit(true)
    try {
      const updated = await renameProject(id, editName.trim())
      setProjects(projects.map(p => p.id === id ? updated : p))
      setEditingId(null)
    } catch (e) {
      alert(`Rename failed: ${e.message}`)
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleDelete(p) {
    if (!confirm(`Delete "${p.name}" and everything inside it? This cannot be undone.`)) return
    try {
      await deleteProject(p.id)
      setProjects(projects.filter(x => x.id !== p.id))
    } catch (e) {
      alert(`Delete failed: ${e.message}`)
    }
  }

  return (
    <section>
      <div className="row">
        <h2>Projects</h2>
        <button onClick={() => setShowNew(true)}>New Project</button>
      </div>

      {loading && <p className="muted">Loading...</p>}
      {error && (
        <div className="error error-row">
          <span>{error}</span>
          <button onClick={load}>Retry</button>
        </div>
      )}
      {!loading && !error && projects.length === 0 && (
        <p className="muted">No projects yet. Create one to get started.</p>
      )}

      <ul className="doc-list">
        {projects.map((p) => (
          <li key={p.id}>
            {editingId === p.id ? (
              <div className="title-edit-group dashboard-edit">
                <input
                  className="title-edit-input"
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  disabled={savingEdit}
                  autoFocus
                />
                <button onClick={() => saveRename(p.id, p.name)} disabled={savingEdit}>Save</button>
                <button onClick={() => setEditingId(null)} disabled={savingEdit}>Cancel</button>
              </div>
            ) : (
              <>
                <button className="link" onClick={() => openProject(p)}>
                  {p.name}
                </button>
                <div className="doc-list-right">
                  <span className="muted">{formatDate(p.created_at)}</span>
                  <button
                    className="pencil-btn"
                    onClick={() => { setEditName(p.name); setEditingId(p.id) }}
                    title="Rename project"
                  >
                    ✎
                  </button>
                  <button
                    className="pencil-btn"
                    onClick={() => handleDelete(p)}
                    title="Delete project"
                  >
                    ✕
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>

      {showNew && (
        <Modal title="New Project" onClose={() => setShowNew(false)}>
          <form onSubmit={submitNew}>
            <label>
              Name
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Acme Engagement"
                autoFocus
              />
            </label>
            <div className="row end">
              <button type="button" onClick={() => setShowNew(false)} disabled={creating}>
                Cancel
              </button>
              <button type="submit" disabled={!newName.trim() || creating}>
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  )
}

function formatDate(iso) {
  try { return new Date(iso).toLocaleDateString() } catch { return iso }
}
