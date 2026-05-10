import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import DocumentDashboard from '../components/DocumentDashboard.jsx'
import * as api from '../api.js'

// Wrap component in a router since it uses useNavigate
function renderDashboard() {
  return render(
    <MemoryRouter>
      <DocumentDashboard />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('DocumentDashboard', () => {
  it('shows a loading state initially', () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([])
    renderDashboard()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows an empty state message when there are no documents', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([])
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument()
    })
  })

  it('renders a list of document titles', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([
      { id: 1, title: 'Service Agreement', updated_at: new Date().toISOString() },
      { id: 2, title: 'NDA Policy', updated_at: new Date().toISOString() },
    ])
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('Service Agreement')).toBeInTheDocument()
      expect(screen.getByText('NDA Policy')).toBeInTheDocument()
    })
  })

  it('shows an error message when the API fails', async () => {
    vi.spyOn(api, 'listDocuments').mockRejectedValue(new Error('server error'))
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('server error')).toBeInTheDocument()
    })
  })

  it('renders a "New Document" button', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([])
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new document/i })).toBeInTheDocument()
    })
  })
})
