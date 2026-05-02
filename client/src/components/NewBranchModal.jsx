import { useState } from 'react'
import Modal from './Modal.jsx'
import { createBranch } from '../api.js'
import { emit } from '../events.js'

export default function NewBranchModal({ documentId, sourceBranchId, onClose, onCreated }) {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function submit(e) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Branch name is required')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const branch = await createBranch(documentId, trimmed, sourceBranchId)
      emit('branch-created', branch)
      onCreated(branch)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="New Branch" onClose={onClose}>
      <form onSubmit={submit}>
        <label>
          Name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Liability_Revision"
            autoFocus
          />
        </label>
        {error && <p className="error">{error}</p>}
        <div className="row end">
          <button type="button" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" disabled={saving}>
            {saving ? 'Creating...' : 'Create Branch'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
