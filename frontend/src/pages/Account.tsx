import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Account() {
  const { user, loading, logout } = useAuth()

  if (loading) return <section className="section muted">Loading…</section>
  if (!user) return <Navigate to="/login" replace />

  return (
    <section className="section narrow">
      <h1 className="page-title">Welcome, {user.first_name}!</h1>
      <p className="lead">You're logged in to Campus Customs.</p>
      <div className="auth-card account-card">
        <dl>
          <dt>Name</dt>
          <dd>
            {user.first_name} {user.last_name}
          </dd>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </dl>
        <Link to="/products" className="btn btn-primary">
          Start shopping
        </Link>
        <button className="btn btn-secondary" onClick={logout}>
          Log out
        </button>
      </div>
    </section>
  )
}
