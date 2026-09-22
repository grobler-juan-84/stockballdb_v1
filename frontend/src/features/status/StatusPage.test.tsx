import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StatusPage } from './StatusPage'
import * as client from '../../client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('StatusPage', () => {
  it('shows API unreachable when readiness fails', async () => {
    vi.spyOn(client, 'fetchReady').mockRejectedValue(
      client.ClientError.network('backend unreachable'),
    )

    render(
      <MemoryRouter>
        <StatusPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('API unreachable')).toBeInTheDocument()
    })
    expect(
      screen.getByText(/HTTP transport is down/i),
    ).toBeInTheDocument()
  })

  it('distinguishes DB unavailable from API reachable', async () => {
    vi.spyOn(client, 'fetchReady').mockResolvedValue({
      ready: true,
      service: 'stockballdb-api',
    })
    vi.spyOn(client, 'fetchStatus').mockResolvedValue({
      available: false,
      database_connected: false,
      health_status: null,
      validate_v1_pass: null,
      alembic_head: null,
      expected_alembic_head: null,
      calendar_version: null,
      finding_counts: {},
      error_message: 'database unavailable: test',
    })

    render(
      <MemoryRouter>
        <StatusPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Reachable')).toBeInTheDocument()
    })
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
    expect(
      screen.getByText(/API is reachable, but the application reports/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/database unavailable: test/i)).toBeInTheDocument()
  })
})
