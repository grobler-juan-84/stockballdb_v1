import { apiGet } from './http'
import type { ApplicationStatus, Instrument, ReadyResponse } from './types'

export function fetchReady(): Promise<ReadyResponse> {
  return apiGet<ReadyResponse>('/ready')
}

export function fetchStatus(): Promise<ApplicationStatus> {
  return apiGet<ApplicationStatus>('/api/status')
}

export function fetchInstruments(): Promise<Instrument[]> {
  return apiGet<Instrument[]>('/api/catalog/instruments')
}
