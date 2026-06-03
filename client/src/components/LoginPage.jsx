import { useState, useMemo } from 'react'
import { login, register } from '../api.js'

const PASSWORD_RULES = [
  { label: 'At least 8 characters', test: (pw) => pw.length >= 8 },
  { label: 'One lowercase letter (a–z)', test: (pw) => /[a-z]/.test(pw) },
  { label: 'One uppercase letter (A–Z)', test: (pw) => /[A-Z]/.test(pw) },
  { label: 'One digit (0–9)', test: (pw) => /\d/.test(pw) },
  { label: 'One special character (!@#$…)', test: (pw) => /[^a-zA-Z0-9]/.test(pw) },
]

export default function LoginPage({ onLoggedIn }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const isSignUp = mode === 'signup'

  const ruleResults = useMemo(
    () => PASSWORD_RULES.map((rule) => ({ ...rule, passed: rule.test(password) })),
    [password],
  )

  const allRulesPassed = ruleResults.every((r) => r.passed)

  function validate() {
    if (!email) return 'Email is required'
    if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email)) return 'Please enter a valid email address (e.g. you@example.com)'

    if (isSignUp) {
      if (!firstName.trim()) return 'First name is required'
      if (!lastName.trim()) return 'Last name is required'
      if (!allRulesPassed) return 'Please satisfy all password requirements'
    }

    if (!isSignUp && password.length < 8) return 'Password must be at least 8 characters'
    return null
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = isSignUp
        ? await register(email, firstName.trim(), lastName.trim(), password)
        : await login(email, password)
      onLoggedIn(result.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="login-section">
      <div className="login-card">
        <h2>{isSignUp ? 'Create Account' : 'Sign In'}</h2>
        <p className="login-subtitle">
          {isSignUp
            ? 'Set up your DocuCommit account'
            : 'Log in to access your documents'}
        </p>

        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input
              id="login-email"
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. frank@example.com"
              autoComplete="email"
              autoFocus
            />
          </label>

          {isSignUp && (
            <>
              <div className="login-name-row">
                <label>
                  First Name
                  <input
                    id="login-first-name"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g. Frank"
                    autoComplete="given-name"
                  />
                </label>
                <label>
                  Last Name
                  <input
                    id="login-last-name"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g. Smith"
                    autoComplete="family-name"
                  />
                </label>
              </div>
            </>
          )}

          <label>
            Password
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(null) }}
              placeholder="Enter your password"
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
            />
          </label>

          {isSignUp && (
            <ul className="pw-rules" id="password-rules">
              {ruleResults.map((rule, i) => (
                <li key={i} className={rule.passed ? 'pw-rule passed' : 'pw-rule'}>
                  <span className="pw-rule-icon" aria-hidden="true">
                    {rule.passed ? '✓' : '✗'}
                  </span>
                  {rule.label}
                </li>
              ))}
            </ul>
          )}

          {error && <p className="error">{error}</p>}

          <button id="login-submit" type="submit" disabled={loading || !email || !password}>
            {loading ? 'Please wait...' : isSignUp ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <p className="login-toggle">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            className="link"
            type="button"
            onClick={() => {
              setMode(isSignUp ? 'login' : 'signup')
              setError(null)
            }}
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </section>
  )
}
