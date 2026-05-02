import { useEffect, useState } from 'react'
import BranchPicker from './BranchPicker.jsx'
import CommitRevisionModal from './CommitRevisionModal.jsx'
import NewBranchModal from './NewBranchModal.jsx'

export default function Editor({ doc, branch, onBack, onSwitchBranch }) {
  const [content, setContent] = useState(branch.current_content)
  const [baseline, setBaseline] = useState(branch.current_content)
  const [showCommit, setShowCommit] = useState(false)
  const [showNewBranch, setShowNewBranch] = useState(false)

  useEffect(() => {
    setContent(branch.current_content)
    setBaseline(branch.current_content)
  }, [branch.id])

  const dirty = content !== baseline

  function trySwitch(next) {
    if (next.id === branch.id) return
    if (dirty && !window.confirm('You have uncommitted changes. Switch branches anyway?')) return
    onSwitchBranch(next)
  }

  function handleCommitted() {
    setBaseline(content)
    setShowCommit(false)
  }

  function handleBranchCreated(newBranch) {
    setShowNewBranch(false)
    onSwitchBranch(newBranch)
  }

  return (
    <section>
      <div className="row">
        <div className="left-group">
          <button onClick={onBack}>Back</button>
          <BranchPicker
            documentId={doc.id}
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
          documentId={doc.id}
          sourceBranchId={branch.id}
          onClose={() => setShowNewBranch(false)}
          onCreated={handleBranchCreated}
        />
      )}
    </section>
  )
}
