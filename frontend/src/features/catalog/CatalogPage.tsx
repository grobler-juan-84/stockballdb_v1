import { useEffect, useState } from 'react'
import {
  ClientError,
  fetchInstruments,
  isClientError,
  type Instrument,
} from '../../client'
import { ErrorBlock, LoadingBlock } from '../../components/StateBlocks'

type LoadState =
  | { phase: 'loading' }
  | { phase: 'error'; error: ClientError }
  | { phase: 'success'; instruments: Instrument[] }

export function CatalogPage() {
  const [state, setState] = useState<LoadState>({ phase: 'loading' })

  useEffect(() => {
    let cancelled = false

    async function load() {
      setState({ phase: 'loading' })
      try {
        const instruments = await fetchInstruments()
        if (!cancelled) {
          setState({ phase: 'success', instruments })
        }
      } catch (err) {
        if (cancelled) return
        const error = isClientError(err)
          ? err
          : ClientError.network('backend unreachable', err)
        setState({ phase: 'error', error })
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section>
      <h2>Instrument catalog</h2>
      <p className="muted">
        Read-only list from <code>GET /api/catalog/instruments</code> (not Explorer).
      </p>

      {state.phase === 'loading' ? (
        <LoadingBlock label="Loading instruments…" />
      ) : null}

      {state.phase === 'error' ? (
        <ErrorBlock
          title={state.error.isNetworkFailure ? 'API unreachable' : 'Catalog error'}
          message={state.error.message}
        />
      ) : null}

      {state.phase === 'success' ? (
        <>
          <p>
            <strong>{state.instruments.length}</strong> instrument
            {state.instruments.length === 1 ? '' : 's'} from backend
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Asset type</th>
                  <th>Close only</th>
                </tr>
              </thead>
              <tbody>
                {state.instruments.map((row) => (
                  <tr key={row.symbol}>
                    <td>{row.symbol}</td>
                    <td>{row.asset_type}</td>
                    <td>{row.close_only ? 'yes' : 'no'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  )
}
