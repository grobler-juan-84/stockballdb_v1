import { Navigate, Route, Routes } from 'react-router-dom'
import { CatalogPage } from './features/catalog/CatalogPage'
import { AppShell } from './features/shell/AppShell'
import { StatusPage } from './features/status/StatusPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/status" replace />} />
        <Route path="status" element={<StatusPage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="*" element={<Navigate to="/status" replace />} />
      </Route>
    </Routes>
  )
}
