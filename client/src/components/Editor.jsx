import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDocument, listBranches } from '../api.js'
import { slugify } from '../utils.js'
import RichEditor from './RichEditor.jsx'
import BranchPicker from './BranchPicker.jsx'
import CommitRevisionModal from './CommitRevisionModal.jsx'
import NewBranchModal from './NewBranchModal.jsx'
import CommitHistorySidebar from './CommitHistorySidebar.jsx'
import Modal from './Modal.jsx'

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
  const [pendingSwitch, setPendingSwitch] = useState(null)

  function load() {
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
  }

  useEffect(() => { load() }, [docId, branchName])

  const dirty = content !== baseline

  function goTo(next) {
    navigate(`/${slugify(doc.title)}/${docId}/branches/${slugify(next.name)}`)
  }

  function trySwitch(next) {
    if (slugify(next.name) === branchName) return
    if (dirty) {
      setPendingSwitch(next)
      return
    }
    goTo(next)
  }

  function handleCommitted() {
    setBaseline(content)
    setShowCommit(false)
    if (pendingSwitch) {
      const next = pendingSwitch
      setPendingSwitch(null)
      goTo(next)
    }
  }

  function handleBranchCreated(newBranch) {
    setShowNewBranch(false)
    navigate(`/${slugify(doc.title)}/${docId}/branches/${slugify(newBranch.name)}`)
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
          <button onClick={() => navigate('/')}>Back</button>
          <BranchPicker
            documentId={parseInt(docId)}
            currentBranchId={branch.id}
            onSelect={trySwitch}
          />
          <button onClick={() => setShowNewBranch(true)}>New Branch</button>
        </div>
        <div className="left-group">
          {!branch.is_main && (
            <button
              id="compare-to-main-btn"
              onClick={() => navigate(`/${slugify(doc.title)}/${docId}/branches/${branchName}/diff`)}
            >
              Compare to Main
            </button>
          )}
          {!branch.is_main && (
            <button
              onClick={() => navigate(`/${slugify(doc.title)}/${docId}/branches/${branchName}/merge`)}
            >
              Merge to Main
            </button>
          )}
          <button onClick={() => setShowCommit(true)} disabled={!dirty}>
            Commit Revision
          </button>
        </div>
      </div>
      <h2 className="doc-title">
        {doc.title}
        {dirty && <span className="dirty-dot" title="Uncommitted changes" />}
        <span className="doc-title-branch">on {branch.name}</span>
      </h2>
      <div className="editor-layout">
        <div className="editor-main">
          <textarea
            className="editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={24}
          />
          {!dirty && <p className="muted">All changes committed.</p>}
        </div>
        <CommitHistorySidebar branchId={branch.id} />
      </div>
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
          sourceBranch={branch}
          onClose={() => setShowNewBranch(false)}
          onCreated={handleBranchCreated}
        />
      )}
      {pendingSwitch && !showCommit && (
        <Modal title="Uncommitted changes" onClose={() => setPendingSwitch(null)}>
          <p>
            You have uncommitted changes on <strong>{branch.name}</strong>.
            Switching to <strong>{pendingSwitch.name}</strong> will discard them
            unless you commit first.
          </p>
          <div className="row end">
            <button onClick={() => setPendingSwitch(null)}>Cancel</button>
            <button
              onClick={() => {
                const next = pendingSwitch
                setPendingSwitch(null)
                goTo(next)
              }}
            >
              Discard and switch
            </button>
            <button onClick={() => setShowCommit(true)}>Commit first</button>
          </div>
        </Modal>
      )}
    </section>
  )
}
