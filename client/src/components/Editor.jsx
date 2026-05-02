import { useState } from 'react'
import { updateDocument } from '../api.js'
import { emit } from '../events.js'

export default function Editor({ doc, onBack }) {
  const [title, setTitle] = useState(doc.title)
  const [content, setContent] = useState(doc.content)
  const [baseline, setBaseline] = useState({ title: doc.title, content: doc.content })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [savedOnce, setSavedOnce] = useState(false)

  const dirty = title !== baseline.title || content !== baseline.content

  async function save() {
    if (!title.trim()) {
      setError('Title is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const updated = await updateDocument(doc.id, { title: title.trim(), content })
      setBaseline({ title: updated.title, content: updated.content })
      setTitle(updated.title)
      setSavedOnce(true)
      emit('document-changed')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <div className="row">
        <button onClick={onBack}>Back</button>
        <button onClick={save} disabled={saving || !dirty}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
      <input
        className="title-input"
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        className="editor"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={24}
      />
      {error && <p className="error">{error}</p>}
      {savedOnce && !dirty && !error && <p className="muted">Saved.</p>}
    </section>
  )
}
