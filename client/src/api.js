async function send(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(path, opts)
  if (!res.ok) {
    let payload
    try { payload = await res.json() } catch { payload = {} }
    throw new Error(payload.error || `request failed (${res.status})`)
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Auth ──

export function register(username, password) {
  return send('POST', '/api/auth/register', { username, password })
}

export function login(username, password) {
  return send('POST', '/api/auth/login', { username, password })
}

export function logout() {
  return send('POST', '/api/auth/logout')
}

export function getMe() {
  return send('GET', '/api/auth/me')
}

// ── Documents ──

export function listDocuments() {
  return send('GET', '/api/documents')
}

export function getDocument(id) {
  return send('GET', `/api/documents/${id}`)
}

export function listDocumentCommits(documentId) {
  return send('GET', `/api/documents/${documentId}/commits`)
}

export function createDocument(title, content) {
  return send('POST', '/api/documents', { title, content })
}

export function listBranches(documentId) {
  return send('GET', `/api/documents/${documentId}/branches`)
}

export function createBranch(documentId, name, sourceBranchId) {
  const body = { name }
  if (sourceBranchId !== undefined && sourceBranchId !== null) {
    body.source_branch_id = sourceBranchId
  }
  return send('POST', `/api/documents/${documentId}/branches`, body)
}

export function getBranch(branchId) {
  return send('GET', `/api/branches/${branchId}`)
}

export function createCommit(branchId, message, content) {
  return send('POST', `/api/branches/${branchId}/commits`, { message, content })
}

export function listCommits(branchId) {
  return send('GET', `/api/branches/${branchId}/commits`)
}

export function diffBranch(branchId, ignoreWhitespace = false) {
  const qs = ignoreWhitespace ? '?w=1' : ''
  return send('GET', `/api/branches/${branchId}/diff${qs}`)
}

export function mergeBranch(branchId) {
  return send('POST', `/api/branches/${branchId}/merge`)
}
