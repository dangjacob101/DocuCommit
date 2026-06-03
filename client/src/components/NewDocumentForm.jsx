import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createDocument, listBranches } from '../api.js'
import { slugify } from '../utils.js'

export default function NewDocumentForm() {
  const { projectSlug, projectId } = useParams()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const cancelTo = projectId ? `/${projectSlug}/${projectId}` : '/'

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) {
      setError('Title is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const doc = await createDocument(title.trim(), content, projectId ? parseInt(projectId) : undefined)
      const branches = await listBranches(doc.id)
      const main = branches.find(b => b.name === 'Main') || branches[0]
      navigate(`/${projectSlug}/${projectId}/${slugify(title)}/${doc.id}/branches/${slugify(main.name)}`)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <section>
      <h2>New Document</h2>
      <form onSubmit={submit}>
        <label>
          Title
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Acme Services Agreement"
            autoFocus
          />
        </label>
        <label>
          Initial text
          <textarea
            className="editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            placeholder="Start typing the document..."
          />
        </label>
        {error && <p className="error">{error}</p>}
        <div className="row end">
          <button type="button" onClick={() => navigate(cancelTo)} disabled={saving}>
            Cancel
          </button>
          <button type="submit" disabled={!title.trim() || saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </section>
  )
}
