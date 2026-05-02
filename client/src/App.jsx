import { useEffect, useState } from 'react'
import DocumentDashboard from './components/DocumentDashboard.jsx'
import NewDocumentForm from './components/NewDocumentForm.jsx'
import Editor from './components/Editor.jsx'
import { listBranches } from './api.js'
import { on, off } from './events.js'

export default function App() {
  const [view, setView] = useState({ name: 'dashboard' })

  async function openDocument(doc) {
    try {
      const branches = await listBranches(doc.id)
      const main = branches.find(b => b.name === 'Main') || branches[0]
      setView({ name: 'editor', doc, branch: main })
    } catch (e) {
      alert(e.message)
    }
  }

  useEffect(() => {
    on('open-document', openDocument)
    return () => off('open-document', openDocument)
  }, [])

  function switchBranch(branch) {
    setView(v => ({ ...v, branch }))
  }

  return (
    <div className="app">
      <header>
        <h1>DocuCommit</h1>
      </header>
      <main>
        {view.name === 'dashboard' && (
          <DocumentDashboard onNew={() => setView({ name: 'new' })} />
        )}
        {view.name === 'new' && (
          <NewDocumentForm
            onCancel={() => setView({ name: 'dashboard' })}
            onCreated={openDocument}
          />
        )}
        {view.name === 'editor' && (
          <Editor
            doc={view.doc}
            branch={view.branch}
            onBack={() => setView({ name: 'dashboard' })}
            onSwitchBranch={switchBranch}
          />
        )}
      </main>
    </div>
  )
}
