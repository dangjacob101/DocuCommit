import { useEffect, useState } from 'react'
import { listBranches } from '../api.js'
import { on, off } from '../events.js'

export default function BranchPicker({ documentId, currentBranchId, onSelect }) {
  const [branches, setBranches] = useState([])

  async function load() {
    try {
      const rows = await listBranches(documentId)
      setBranches(rows)
    } catch {
      setBranches([])
    }
  }

  useEffect(() => {
    load()
    const refresh = () => load()
    on('branch-created', refresh)
    return () => off('branch-created', refresh)
  }, [documentId])

  function handleChange(e) {
    const id = parseInt(e.target.value, 10)
    const next = branches.find(b => b.id === id)
    if (next) onSelect(next)
  }

  return (
    <select className="branch-picker" value={currentBranchId} onChange={handleChange}>
      {branches.map(b => (
        <option key={b.id} value={b.id}>{b.name}</option>
      ))}
    </select>
  )
}
