import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { getMe, logout as apiLogout } from './api.js'
import LoginPage from './components/LoginPage.jsx'
import DocumentDashboard from './components/DocumentDashboard.jsx'
import NewDocumentForm from './components/NewDocumentForm.jsx'
import Editor from './components/Editor.jsx'
import DiffViewer from './components/DiffViewer.jsx'

export default function App() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    getMe()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  async function handleLogout() {
    await apiLogout()
    setUser(null)
  }

  if (checking) {
    return (
      <div className="app">
        <header><h1>DocuCommit</h1></header>
        <main><p className="muted">Loading...</p></main>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="app">
        <header><h1>DocuCommit</h1></header>
        <main>
          <LoginPage onLoggedIn={setUser} />
        </main>
      </div>
    )
  }

  return (
    <div className="app">
      <header>
        <h1>DocuCommit</h1>
        <div className="header-right">
          <span className="header-user">{user.username}</span>
          <button id="logout-btn" className="logout-btn" onClick={handleLogout}>Log Out</button>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<DocumentDashboard />} />
          <Route path="/create-new-document" element={<NewDocumentForm />} />
          <Route path="/:docSlug/:docId/branches/:branchName" element={<Editor />} />
          <Route path="/:docSlug/:docId/branches/:branchName/diff" element={<DiffViewer />} />
        </Routes>
      </main>
    </div>
  )
}
