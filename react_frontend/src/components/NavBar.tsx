import { NavLink } from 'react-router-dom'
import './NavBar.css'

const links = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/patient', label: 'Patient' },
  { to: '/query', label: 'Query' },
  { to: '/feedback', label: 'Feedback' },
  { to: '/settings', label: 'Settings' },
  { to: '/login', label: 'Login' },
]

const NavBar = () => {
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
    </nav>
  )
}

export default NavBar
