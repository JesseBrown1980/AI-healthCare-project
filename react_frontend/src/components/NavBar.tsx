import { NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'
import './NavBar.css'

const links = [
  { to: '/', labelKey: 'ui.nav.home' },
  { to: '/dashboard', labelKey: 'ui.nav.dashboard' },
  { to: '/patient', labelKey: 'ui.nav.patient' },
  { to: '/query', labelKey: 'ui.nav.query' },
  { to: '/feedback', labelKey: 'ui.nav.feedback' },
  { to: '/settings', labelKey: 'ui.nav.settings' },
]

const NavBar = () => {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { isAuthenticated, userEmail, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="navbar__brand">{t('ui.nav.brand', { defaultValue: 'AI Healthcare' })}</div>
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
            {t(link.labelKey, { defaultValue: link.labelKey })}
          </NavLink>
        ))}
      </div>
      <div className="navbar__actions">
        {isAuthenticated ? (
          <>
            <span className="navbar__user">{userEmail || t('ui.nav.signed_in_user', { defaultValue: 'Signed in user' })}</span>
            <button type="button" className="navbar__button" onClick={handleLogout}>
              {t('auth.logout', { defaultValue: 'Logout' })}
            </button>
          </>
        ) : (
          <NavLink
            to="/login"
            className={({ isActive }) =>
              isActive ? 'navbar__link navbar__link--active' : 'navbar__link'
            }
          >
            {t('auth.login', { defaultValue: 'Login' })}
          </NavLink>
        )}
      </div>
    </nav>
  )
}

export default NavBar
