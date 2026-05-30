import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginPage from '../components/LoginPage.jsx'
import * as api from '../api.js'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('LoginPage', () => {
  it('toggles to sign up mode and displays password rules', async () => {
    const user = userEvent.setup()
    render(<LoginPage onLoggedIn={vi.fn()} />)

    // Switch to sign up
    await user.click(screen.getByRole('button', { name: /sign up/i }))

    // Rules should be visible
    expect(screen.getByText('At least 8 characters')).toBeInTheDocument()
    expect(screen.getByText('One lowercase letter (a–z)')).toBeInTheDocument()
    expect(screen.getByText('One uppercase letter (A–Z)')).toBeInTheDocument()
    expect(screen.getByText('One digit (0–9)')).toBeInTheDocument()
    expect(screen.getByText('One special character (!@#$…)')).toBeInTheDocument()
  })

  it('updates password rule checklist correctly', async () => {
    const user = userEvent.setup()
    render(<LoginPage onLoggedIn={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /sign up/i }))

    const passwordInput = screen.getByLabelText(/password/i)
    
    // Type exactly 8 characters
    await user.type(passwordInput, '12345678')

    // Find the 8 characters rule list item
    const rule8Chars = screen.getByText('At least 8 characters').closest('li')
    
    // It should have the "passed" class and display a ✓
    expect(rule8Chars).toHaveClass('passed')
    expect(rule8Chars).toHaveTextContent('✓')

    // The other rules should fail
    const ruleLower = screen.getByText('One lowercase letter (a–z)').closest('li')
    expect(ruleLower).not.toHaveClass('passed')
    expect(ruleLower).toHaveTextContent('✗')
  })
})
