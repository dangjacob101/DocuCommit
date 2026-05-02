import { useState } from 'react'
import { createDocument } from '../api.js'
import { emit } from '../events.js'

export default function NewDocumentForm({ onCancel, onCreated }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) {
      setError('Title is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const doc = await createDocument(title.trim(), content)
      emit('document-changed')
      onCreated(doc)
    } catch (err) {
      setError(err.message)
    } finally {
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
          <button type="button" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </section>
  )
}
