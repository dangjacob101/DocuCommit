import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import NewDocumentForm from '../components/NewDocumentForm.jsx'
import * as api from '../api.js'

function renderForm() {
  return render(
    <MemoryRouter>
      <NewDocumentForm />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('NewDocumentForm', () => {
  it('renders a title input and rich-text editor', () => {
    renderForm()
    expect(screen.getByPlaceholderText(/acme services agreement/i)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /start typing the document/i })).toBeInTheDocument()
  })

  it('disables the Save button when the title is empty', () => {
    renderForm()
    expect(screen.getByRole('button', { name: /save/i })).toBeDisabled()
  })

  it('enables the Save button when a title is typed', async () => {
    const user = userEvent.setup()
    renderForm()
    await user.type(screen.getByPlaceholderText(/acme services agreement/i), 'My Contract')
    expect(screen.getByRole('button', { name: /save/i })).not.toBeDisabled()
  })

  it('calls createDocument and listBranches on submit', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'createDocument').mockResolvedValue({ id: 1, title: 'My Contract' })
    vi.spyOn(api, 'listBranches').mockResolvedValue([{ id: 1, name: 'Main' }])
    renderForm()
    await user.type(screen.getByPlaceholderText(/acme services agreement/i), 'My Contract')
    await user.click(screen.getByRole('button', { name: /save/i }))
    await waitFor(() => {
      expect(api.createDocument).toHaveBeenCalledWith('My Contract', '', undefined)
      expect(api.listBranches).toHaveBeenCalledWith(1)
    })
  })

  it('shows an error message when createDocument fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'createDocument').mockRejectedValue(new Error('title is required'))
    renderForm()
    await user.type(screen.getByPlaceholderText(/acme services agreement/i), 'X')
    await user.click(screen.getByRole('button', { name: /save/i }))
    await waitFor(() => {
      expect(screen.getByText('title is required')).toBeInTheDocument()
    })
  })

  it('renders a Cancel button', () => {
    renderForm()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })
})
