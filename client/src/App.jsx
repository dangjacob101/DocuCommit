import { useEffect, useState, useRef } from 'react'
import { Routes, Route } from 'react-router-dom'
import { getMe, logout as apiLogout, uploadProfilePicture } from './api.js'
import LoginPage from './components/LoginPage.jsx'
import ProjectDashboard from './components/ProjectDashboard.jsx'
import ProjectView from './components/ProjectView.jsx'
import NewDocumentForm from './components/NewDocumentForm.jsx'
import Editor from './components/Editor.jsx'
import DiffViewer from './components/DiffViewer.jsx'
import ConflictResolver from './components/ConflictResolver.jsx'

export default function App() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    getMe()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setChecking(false))
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
    await apiLogout()
    setUser(null)
    setMenuOpen(false)
  }

  function handleUploadClick() {
    fileInputRef.current?.click()
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await uploadProfilePicture(file)
      setUser(result.user)
    } catch (err) {
      alert(err.message)
    }
    // Reset the input so the same file can be re-selected
    e.target.value = ''
    setMenuOpen(false)
  }

  function getInitials() {
    const first = user?.first_name?.[0] || ''
    const last = user?.last_name?.[0] || ''
    return (first + last).toUpperCase() || '?'
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
          <div className="profile-menu" ref={menuRef}>
            <button
              className="profile-avatar-btn"
              id="profile-avatar-btn"
              onClick={() => setMenuOpen((prev) => !prev)}
              aria-label="Profile menu"
            >
              {user.profile_picture_url ? (
                <img
                  src={user.profile_picture_url}
                  alt="Profile"
                  className="profile-avatar-img"
                />
              ) : (
                <span className="profile-avatar-initials">{getInitials()}</span>
              )}
            </button>

            {menuOpen && (
              <div className="profile-dropdown" id="profile-dropdown">
                <div className="profile-dropdown-header">
                  <div className="profile-dropdown-avatar">
                    {user.profile_picture_url ? (
                      <img
                        src={user.profile_picture_url}
                        alt="Profile"
                        className="profile-avatar-img"
                      />
                    ) : (
                      <span className="profile-avatar-initials">{getInitials()}</span>
                    )}
                  </div>
                  <div className="profile-dropdown-info">
                    <span className="profile-dropdown-name">
                      {user.first_name} {user.last_name}
                    </span>
                    <span className="profile-dropdown-email">{user.email}</span>
                  </div>
                </div>
                <div className="profile-dropdown-divider" />
                <button
                  className="profile-dropdown-item"
                  id="upload-photo-btn"
                  onClick={handleUploadClick}
                >
                  Upload Profile Picture
                </button>
                <button
                  className="profile-dropdown-item profile-dropdown-logout"
                  id="logout-btn"
                  onClick={handleLogout}
                >
                  Log Out
                </button>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
          </div>
          <span className="header-user">{user.first_name} {user.last_name}</span>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<ProjectDashboard />} />
          <Route path="/:projectSlug/:projectId" element={<ProjectView />} />
          <Route path="/:projectSlug/:projectId/new-document" element={<NewDocumentForm />} />
          <Route path="/:projectSlug/:projectId/:docSlug/:docId/branches/:branchName" element={<Editor />} />
          <Route path="/:projectSlug/:projectId/:docSlug/:docId/branches/:branchName/diff" element={<DiffViewer />} />
          <Route path="/:projectSlug/:projectId/:docSlug/:docId/branches/:branchName/merge" element={<ConflictResolver />} />
        </Routes>
      </main>
    </div>
  )
}
