import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './NavBar.css'

const links = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/patient', label: 'Patient' },
  { to: '/query', label: 'Query' },
  { to: '/feedback', label: 'Feedback' },
  { to: '/settings', label: 'Settings' },
]

const NavBar = () => {
  const navigate = useNavigate()
  const { isAuthenticated, userEmail, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="navbar__brand">AI Healthcare</div>
      <div className="navbar__links">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              isActive ? 'navbar__link navbar__link--active' : 'navbar__link'
            }
            end={link.to === '/'}
          >
            {link.label}
          </NavLink>
        ))}
      </div>
      <div className="navbar__actions">
        {isAuthenticated ? (
          <>
            <span className="navbar__user">{userEmail || 'Signed in user'}</span>
            <button type="button" className="navbar__button" onClick={handleLogout}>
              Logout
            </button>
          </>
        ) : (
          <NavLink
            to="/login"
            className={({ isActive }) =>
              isActive ? 'navbar__link navbar__link--active' : 'navbar__link'
            }
          >
            Login
          </NavLink>
        )}
      </div>
    </nav>
  )
}

export default NavBar
