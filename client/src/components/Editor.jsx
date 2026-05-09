import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDocument, listBranches } from '../api.js'
import { slugify } from '../utils.js'
import BranchPicker from './BranchPicker.jsx'
import CommitRevisionModal from './CommitRevisionModal.jsx'
import NewBranchModal from './NewBranchModal.jsx'

export default function Editor() {
  const { docId, branchName } = useParams()
  const navigate = useNavigate()

  const [doc, setDoc] = useState(null)
  const [branch, setBranch] = useState(null)
  const [content, setContent] = useState('')
  const [baseline, setBaseline] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCommit, setShowCommit] = useState(false)
  const [showNewBranch, setShowNewBranch] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([getDocument(parseInt(docId)), listBranches(parseInt(docId))])
      .then(([docData, branches]) => {
        const branchData = branches.find(b => slugify(b.name) === branchName)
        if (!branchData) throw new Error(`Branch "${branchName}" not found`)
        setDoc(docData)
        setBranch(branchData)
        setContent(branchData.current_content)
        setBaseline(branchData.current_content)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId, branchName])

  const dirty = content !== baseline

  function trySwitch(next) {
    if (slugify(next.name) === branchName) return
    if (dirty && !window.confirm('You have uncommitted changes. Switch branches anyway?')) return
    navigate(`/${slugify(doc.title)}/${docId}/branches/${slugify(next.name)}`)
  }

  function handleCommitted() {
    setBaseline(content)
    setShowCommit(false)
  }

  function handleBranchCreated(newBranch) {
    setShowNewBranch(false)
    navigate(`/${slugify(doc.title)}/${docId}/branches/${slugify(newBranch.name)}`)
  }

  if (loading) return <p className="muted">Loading...</p>
  if (error) return <p className="error">{error}</p>

  return (
    <section>
      <div className="row">
        <div className="left-group">
          <button onClick={() => navigate('/')}>Back</button>
          <BranchPicker
            documentId={parseInt(docId)}
            currentBranchId={branch.id}
            onSelect={trySwitch}
          />
          <button onClick={() => setShowNewBranch(true)}>New Branch</button>
        </div>
        <button onClick={() => setShowCommit(true)} disabled={!dirty}>
          Commit Revision
        </button>
      </div>
      <h2 className="doc-title">{doc.title}</h2>
      <textarea
        className="editor"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={24}
      />
      {!dirty && <p className="muted">All changes committed.</p>}
      {showCommit && (
        <CommitRevisionModal
          branchId={branch.id}
          content={content}
          onClose={() => setShowCommit(false)}
          onCommitted={handleCommitted}
        />
      )}
      {showNewBranch && (
        <NewBranchModal
          documentId={parseInt(docId)}
          sourceBranchId={branch.id}
          onClose={() => setShowNewBranch(false)}
          onCreated={handleBranchCreated}
        />
      )}
    </section>
  )
}
