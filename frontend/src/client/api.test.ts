import { afterEach, describe, expect, it, vi } from 'vitest'
import { ClientError } from './errors'
import { apiGet } from './http'
import { fetchInstruments, fetchReady, fetchStatus } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function mockFetch(handler: (url: string) => Response | Promise<Response>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      return handler(url)
    }),
  )
}

describe('application client', () => {
  it('parses successful readiness response', async () => {
    mockFetch(() =>
      new Response(JSON.stringify({ ready: true, service: 'stockballdb-api' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await expect(fetchReady()).resolves.toEqual({
      ready: true,
      service: 'stockballdb-api',
    })
  })

  it('parses catalog instruments', async () => {
    const rows = [
      { symbol: 'SPY', asset_type: 'etf', close_only: false },
      { symbol: 'WTI', asset_type: 'commodity', close_only: true },
    ]
    mockFetch(() =>
      new Response(JSON.stringify(rows), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await expect(fetchInstruments()).resolves.toEqual(rows)
  })

  it('maps structured API errors', async () => {
    mockFetch(() =>
      new Response(
        JSON.stringify({
          error: { code: 'not_found', message: 'unknown domain', details: {} },
        }),
        { status: 404, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    await expect(apiGet('/api/catalog/domains/x/fields')).rejects.toMatchObject({
      kind: 'api',
      code: 'not_found',
      message: 'unknown domain',
      status: 404,
    })
  })

  it('maps network failure to ClientError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    await expect(fetchStatus()).rejects.toBeInstanceOf(ClientError)
    await expect(fetchStatus()).rejects.toMatchObject({
      kind: 'network',
      message: 'backend unreachable',
    })
  })

  it('parses status unavailable payload without treating it as transport failure', async () => {
    mockFetch(() =>
      new Response(
        JSON.stringify({
          available: false,
          database_connected: false,
          health_status: null,
          validate_v1_pass: null,
          alembic_head: null,
          expected_alembic_head: null,
          calendar_version: null,
          finding_counts: {},
          error_message: 'database unavailable: boom',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    const status = await fetchStatus()
    expect(status.available).toBe(false)
    expect(status.error_message).toContain('database unavailable')
  })
})
