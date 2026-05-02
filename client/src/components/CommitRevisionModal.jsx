import { useState } from 'react'
import Modal from './Modal.jsx'
import { createCommit } from '../api.js'
import { emit } from '../events.js'

export default function CommitRevisionModal({ branchId, content, onClose, onCommitted }) {
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    const msg = message.trim()
    if (!msg) {
      setError('Commit message is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const commit = await createCommit(branchId, msg, content)
      emit('commit-created', commit)
      onCommitted(commit)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Commit Revision" onClose={onClose}>
      <form onSubmit={submit}>
        <label>
          Message
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="e.g. Updated payment terms"
            autoFocus
          />
        </label>
        {error && <p className="error">{error}</p>}
        <div className="row end">
          <button type="button" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Commit'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
