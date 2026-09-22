/**
 * Single configuration boundary for the FastAPI base URL.
 * Dev default matches P2 (`127.0.0.1:8765`). Electron can override later.
 */
export function getApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL?.trim()
  return raw && raw.length > 0 ? raw.replace(/\/$/, '') : 'http://127.0.0.1:8765'
}
