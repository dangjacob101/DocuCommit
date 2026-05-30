async function send(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } }
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

export function exportDocument(documentId) {
  return send('GET', `/api/documents/${documentId}/export`)
}

// Mock for now this needs to be changed later when we get real stuff going
export function getMergePreview(documentId, branchName) {
  return Promise.resolve({
    branchName,
    mainName: 'Main',
    hunks: [
      { id: 'h1', kind: 'equal', text: 'Hello world.' },
      { id: 'h2', kind: 'auto-branch', branch: 'Adding a new line on the branch.' },
      { id: 'h3', kind: 'conflict', main: 'The cat is black.', branch: 'The cat is orange.' },
      { id: 'h4', kind: 'equal', text: 'Some unchanged middle paragraph.' },
      { id: 'h5', kind: 'auto-main', main: 'A line only Main has.' },
      { id: 'h6', kind: 'conflict', main: 'We meet on Tuesday.', branch: 'We meet on Friday.' }
    ]
  })
}
