import { getApiBaseUrl } from '../config'
import { ClientError } from './errors'
import type { ApiErrorResponse } from './types'

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!value || typeof value !== 'object') return false
  const error = (value as ApiErrorResponse).error
  return (
    !!error &&
    typeof error === 'object' &&
    typeof error.code === 'string' &&
    typeof error.message === 'string'
  )
}

/**
 * Low-level JSON GET against the StockBallDB API.
 * Components should use `./api` helpers, not this directly.
 */
export async function apiGet<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`

  let response: Response
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    })
  } catch (cause) {
    throw ClientError.network('backend unreachable', cause)
  }

  let payload: unknown
  const text = await response.text()
  try {
    payload = text.length > 0 ? JSON.parse(text) : null
  } catch (cause) {
    throw new ClientError('parse', 'response was not valid JSON', {
      status: response.status,
      cause,
    })
  }

  if (!response.ok) {
    if (isApiErrorResponse(payload)) {
      throw ClientError.fromApiBody(response.status, payload.error)
    }
    throw new ClientError('api', `request failed with HTTP ${response.status}`, {
      status: response.status,
      code: 'http_error',
    })
  }

  return payload as T
}
