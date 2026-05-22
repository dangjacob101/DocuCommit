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
  const [username, setUsername] = useState('')
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
    if (username.length < 3) return 'Username must be at least 3 characters'
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) return 'Username can only contain letters, numbers, underscores, and hyphens'
    if (isSignUp && !allRulesPassed) {
      return 'Please satisfy all password requirements'
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
        ? await register(username, password)
        : await login(username, password)
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
            Username
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. frank"
              autoComplete="username"
              autoFocus
            />
          </label>
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

          <button id="login-submit" type="submit" disabled={loading || !username || !password}>
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
