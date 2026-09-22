import { NavLink, Outlet } from 'react-router-dom'
import { getApiBaseUrl } from '../../config'

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <h1>StockBallDB</h1>
          <p className="subtitle">V2 foundation — Catalog &amp; Status</p>
        </div>
        <nav className="app-nav" aria-label="Primary">
          <NavLink to="/status" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Status
          </NavLink>
          <NavLink to="/catalog" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Catalog
          </NavLink>
        </nav>
        <p className="api-hint">
          API: <code>{getApiBaseUrl()}</code>
        </p>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
