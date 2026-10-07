import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useBag } from '../context/BagContext'

const PROMOS = [
  'Free shipping over $50',
  'Homecoming drop live',
  'Officially licensed Yale apparel',
  'Visit the shop at 57 Broadway, New Haven',
  'Go Bulldogs!',
]

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  const { user, loading, logout } = useAuth()
  const { count: bagCount } = useBag()
  const navigate = useNavigate()

  async function handleLogout() {
    close()
    await logout()
    navigate('/')
  }

  return (
    <header className="header">
      <div className="announcement" role="region" aria-label="Store announcements">
        {/* Screen readers get one plain list; the scrolling copy is decorative. */}
        <p className="sr-only">{PROMOS.join('. ')}</p>
        <div className="marquee" aria-hidden="true">
          {[0, 1].map((copy) => (
            <div className="marquee-track" key={copy}>
              {PROMOS.map((p) => (
                <span key={p}>
                  {p} <b>★</b>
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
      <nav className="nav">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-mark" aria-hidden="true">
            CC
          </span>
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue · Est. New Haven</small>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          ☰
        </button>

        <span className="bag-pill" aria-live="polite" aria-label={`${bagCount} ${bagCount === 1 ? 'item' : 'items'} in your bag`}>
          <span aria-hidden="true">🛍</span> {bagCount}
        </span>

        <div className={`nav-links ${open ? 'open' : ''}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          {loading ? null : user ? (
            <>
              <NavLink to="/account" onClick={close}>
                Hi, {user.first_name}
              </NavLink>
              <button className="nav-button" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Log in
              </NavLink>
              <NavLink to="/signup" className="nav-cta" onClick={close}>
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
