import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CatalogPage } from './CatalogPage'
import * as client from '../../client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CatalogPage', () => {
  it('renders instrument list from client data', async () => {
    vi.spyOn(client, 'fetchInstruments').mockResolvedValue([
      { symbol: 'SPY', asset_type: 'etf', close_only: false },
      { symbol: 'WTI', asset_type: 'commodity', close_only: true },
    ])

    render(
      <MemoryRouter>
        <CatalogPage />
      </MemoryRouter>,
    )

    expect(screen.getByText(/Loading instruments/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(
        screen.getByText((_, el) => el?.textContent === '2 instruments from backend'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('WTI')).toBeInTheDocument()
    expect(screen.getByText('commodity')).toBeInTheDocument()
  })

  it('shows API unreachable state on network failure', async () => {
    vi.spyOn(client, 'fetchInstruments').mockRejectedValue(
      client.ClientError.network('backend unreachable'),
    )

    render(
      <MemoryRouter>
        <CatalogPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('API unreachable')).toBeInTheDocument()
    })
    expect(screen.getByText('backend unreachable')).toBeInTheDocument()
  })
})
