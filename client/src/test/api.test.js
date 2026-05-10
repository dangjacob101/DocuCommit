import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listDocuments,
  getDocument,
  createDocument,
  listBranches,
  createBranch,
  getBranch,
  createCommit,
} from '../api.js'

function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('listDocuments()', () => {
  it('calls GET /api/documents', async () => {
    global.fetch = mockFetch(200, [{ id: 1, title: 'Test' }])
    const result = await listDocuments()
    expect(fetch).toHaveBeenCalledWith('/api/documents', expect.objectContaining({ method: 'GET' }))
    expect(result).toEqual([{ id: 1, title: 'Test' }])
  })
})

describe('getDocument()', () => {
  it('calls GET /api/documents/:id', async () => {
    global.fetch = mockFetch(200, { id: 5, title: 'Contract' })
    const result = await getDocument(5)
    expect(fetch).toHaveBeenCalledWith('/api/documents/5', expect.any(Object))
    expect(result.title).toBe('Contract')
  })
})

describe('createDocument()', () => {
  it('calls POST /api/documents with title and content', async () => {
    global.fetch = mockFetch(201, { id: 2, title: 'New Doc' })
    const result = await createDocument('New Doc', 'Some content')
    expect(fetch).toHaveBeenCalledWith(
      '/api/documents',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ title: 'New Doc', content: 'Some content' }),
      })
    )
    expect(result.id).toBe(2)
  })
})

describe('listBranches()', () => {
  it('calls GET /api/documents/:id/branches', async () => {
    global.fetch = mockFetch(200, [{ id: 1, name: 'Main', is_main: true }])
    const result = await listBranches(3)
    expect(fetch).toHaveBeenCalledWith('/api/documents/3/branches', expect.any(Object))
    expect(result[0].name).toBe('Main')
  })
})

describe('createBranch()', () => {
  it('calls POST with name and source_branch_id when provided', async () => {
    global.fetch = mockFetch(201, { id: 2, name: 'Liability-Revision' })
    await createBranch(1, 'Liability-Revision', 1)
    expect(fetch).toHaveBeenCalledWith(
      '/api/documents/1/branches',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Liability-Revision', source_branch_id: 1 }),
      })
    )
  })

  it('omits source_branch_id when not provided', async () => {
    global.fetch = mockFetch(201, { id: 3, name: 'NewBranch' })
    await createBranch(1, 'NewBranch')
    const call = JSON.parse(fetch.mock.calls[0][1].body)
    expect(call).not.toHaveProperty('source_branch_id')
  })
})

describe('getBranch()', () => {
  it('calls GET /api/branches/:id', async () => {
    global.fetch = mockFetch(200, { id: 7, name: 'Main' })
    const result = await getBranch(7)
    expect(fetch).toHaveBeenCalledWith('/api/branches/7', expect.any(Object))
    expect(result.id).toBe(7)
  })
})

describe('createCommit()', () => {
  it('calls POST /api/branches/:id/commits with message and content', async () => {
    global.fetch = mockFetch(201, { id: 10, message: 'Updated section 3' })
    await createCommit(2, 'Updated section 3', '<p>New text</p>')
    expect(fetch).toHaveBeenCalledWith(
      '/api/branches/2/commits',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ message: 'Updated section 3', content: '<p>New text</p>' }),
      })
    )
  })
})

describe('API error handling', () => {
  it('throws an error with the server error message on non-ok response', async () => {
    global.fetch = mockFetch(404, { error: 'document not found' })
    await expect(getDocument(999)).rejects.toThrow('document not found')
  })

  it('throws a fallback message when server returns no error field', async () => {
    global.fetch = mockFetch(500, {})
    await expect(listDocuments()).rejects.toThrow('request failed (500)')
  })
})
