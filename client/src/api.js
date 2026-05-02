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
  return send('GET', '/documents')
}

export function getDocument(id) {
  return send('GET', `/documents/${id}`)
}

export function createDocument(title, content) {
  return send('POST', '/documents', { title, content })
}

export function updateDocument(id, fields) {
  return send('PUT', `/documents/${id}`, fields)
}
