import { Routes, Route } from 'react-router-dom'
import DocumentDashboard from './components/DocumentDashboard.jsx'
import NewDocumentForm from './components/NewDocumentForm.jsx'
import Editor from './components/Editor.jsx'

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>DocuCommit</h1>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<DocumentDashboard />} />
          <Route path="/create-new-document" element={<NewDocumentForm />} />
          <Route path="/:docSlug/:docId/branches/:branchName" element={<Editor />} />
        </Routes>
      </main>
    </div>
  )
}
