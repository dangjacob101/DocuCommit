import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDocument, listBranches, mergeBranch, updateDocument, exportDocument } from '../api.js'
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
  const [mergeError, setMergeError] = useState(null)
  
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [editTitleVal, setEditTitleVal] = useState('')
  const [savingTitle, setSavingTitle] = useState(false)

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

  async function handleExport() {
    try {
      const data = await exportDocument(parseInt(docId))
      const paragraphs = data.content
        .split('\n')
        .filter(line => line.trim())
        .map(line => `<p>${escapeHtml(line)}</p>`)
        .join('\n')
      const html = `<!doctype html>
<html><head><title>${escapeHtml(data.title)}</title>
<style>
  body { font-family: Georgia, "Times New Roman", serif; max-width: 6.5in; margin: 1in auto; line-height: 1.55; color: #111; }
  h1 { font-size: 18pt; text-align: center; margin: 0 0 0.75in; }
  p { margin: 0 0 0.6em; text-align: justify; }
  @media print { body { margin: 0; padding: 0.5in; } }
</style></head>
<body>
  <h1>${escapeHtml(data.title)}</h1>
  ${paragraphs}
  <script>window.onload = function () { window.print() }</script>
</body></html>`
      const win = window.open('', '_blank')
      if (!win) {
        setError('Pop-up blocked. Allow pop-ups to export.')
        return
      }
      win.document.open()
      win.document.write(html)
      win.document.close()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleSaveTitle() {
    if (!editTitleVal.trim() || editTitleVal === doc.title) {
      setIsEditingTitle(false)
      return
    }
    setSavingTitle(true)
    try {
      const updated = await updateDocument(docId, editTitleVal)
      setDoc(updated)
      setIsEditingTitle(false)
      navigate(`/${slugify(updated.title)}/${docId}/branches/${branchName}`, { replace: true })
    } catch (e) {
      alert(`Failed to update title: ${e.message}`)
    } finally {
      setSavingTitle(false)
    }
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
              onClick={async () => {
                setMergeError(null)
                try {
                  await mergeBranch(branch.id)
                  // Clean merge succeeded — navigate to Main
                  navigate(`/${slugify(doc.title)}/${docId}/branches/main`)
                } catch (e) {
                  // Conflict — redirect to the conflict resolver
                  navigate(`/${slugify(doc.title)}/${docId}/branches/${branchName}/merge`)
                }
              }}
            >
              Merge to Main
            </button>
          )}
          {branch.is_main && (
            <button onClick={handleExport} disabled={dirty} title={dirty ? 'Commit your changes first' : ''}>
              Download PDF
            </button>
          )}
          <button onClick={() => setShowCommit(true)} disabled={!dirty}>
            Commit Revision
          </button>
        </div>
      </div>
      
      {isEditingTitle ? (
        <div className="title-edit-group">
          <input 
            className="title-edit-input" 
            value={editTitleVal} 
            onChange={e => setEditTitleVal(e.target.value)} 
            disabled={savingTitle}
            autoFocus 
          />
          <button onClick={handleSaveTitle} disabled={savingTitle}>Save</button>
          <button onClick={() => setIsEditingTitle(false)} disabled={savingTitle}>Cancel</button>
        </div>
      ) : (
        <h2 className="doc-title">
          <span 
            className="editable-title" 
            onClick={() => {
              setEditTitleVal(doc.title)
              setIsEditingTitle(true)
            }}
            title="Click to rename document"
          >
            {doc.title}
          </span>
          {dirty && <span className="dirty-dot" title="Uncommitted changes" />}
          <span className="doc-title-branch">on {branch.name}</span>
        </h2>
      )}

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
