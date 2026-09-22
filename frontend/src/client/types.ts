/** Transport types matching P2 FastAPI JSON contracts. */

export interface ReadyResponse {
  ready: boolean
  service: string
}

export interface Instrument {
  symbol: string
  asset_type: string
  close_only: boolean
}

export interface ApplicationStatus {
  available: boolean
  database_connected: boolean
  health_status: string | null
  validate_v1_pass: boolean | null
  alembic_head: string | null
  expected_alembic_head: string | null
  calendar_version: string | null
  finding_counts: Record<string, number>
  error_message: string | null
}

export interface ApiErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}

export interface ApiErrorResponse {
  error: ApiErrorBody
}
