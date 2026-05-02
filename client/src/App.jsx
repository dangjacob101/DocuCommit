import { useEffect, useState } from 'react'
import DocumentDashboard from './components/DocumentDashboard.jsx'
import NewDocumentForm from './components/NewDocumentForm.jsx'
import Editor from './components/Editor.jsx'
import { on, off } from './events.js'

export default function App() {
  const [view, setView] = useState({ name: 'dashboard' })

  useEffect(() => {
    const open = (doc) => setView({ name: 'editor', doc })
    on('open-document', open)
    return () => off('open-document', open)
  }, [])

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
            onCreated={(doc) => setView({ name: 'editor', doc })}
          />
        )}
        {view.name === 'editor' && (
          <Editor
            doc={view.doc}
            onBack={() => setView({ name: 'dashboard' })}
          />
        )}
      </main>
    </div>
  )
}
