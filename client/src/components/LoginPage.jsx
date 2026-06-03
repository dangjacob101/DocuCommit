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

        <div className="oauth-divider">
          <span>or</span>
        </div>

        <a
          id="google-oauth-btn"
          className="google-oauth-btn"
          href="/api/auth/google/login"
        >
          <svg className="google-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </a>
      </div>
    </section>
  )
}
