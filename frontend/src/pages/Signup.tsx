import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import type { SignupData } from '../api/client'
import { useAuth } from '../context/AuthContext'

const empty: SignupData = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupData>(empty)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/account" replace />

  const set = (field: keyof SignupData) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await signup(form)
      navigate('/account')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="section">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create account</h1>
        <div className="row">
          <label>
            First name
            <input autoComplete="given-name" value={form.first_name} onChange={set('first_name')} required />
          </label>
          <label>
            Last name
            <input autoComplete="family-name" value={form.last_name} onChange={set('last_name')} required />
          </label>
        </div>
        <label>
          Email
          <input type="email" autoComplete="email" value={form.email} onChange={set('email')} required />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={form.password}
            onChange={set('password')}
            required
          />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={set('confirm_password')}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="hint error">Passwords don't match yet.</span>}
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </section>
  )
}
