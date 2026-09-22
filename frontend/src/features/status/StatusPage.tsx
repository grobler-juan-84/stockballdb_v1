import { useEffect, useState } from 'react'
import {
  ClientError,
  fetchReady,
  fetchStatus,
  isClientError,
  type ApplicationStatus,
  type ReadyResponse,
} from '../../client'
import { ErrorBlock, InfoBlock, LoadingBlock } from '../../components/StateBlocks'

type LoadState =
  | { phase: 'loading' }
  | { phase: 'api_unreachable'; error: ClientError }
  | {
      phase: 'ready'
      ready: ReadyResponse
      status: ApplicationStatus | null
      statusError: ClientError | null
    }

export function StatusPage() {
  const [state, setState] = useState<LoadState>({ phase: 'loading' })

  useEffect(() => {
    let cancelled = false

    async function load() {
      setState({ phase: 'loading' })
      try {
        const ready = await fetchReady()
        if (cancelled) return
        try {
          const status = await fetchStatus()
          if (!cancelled) {
            setState({ phase: 'ready', ready, status, statusError: null })
          }
        } catch (err) {
          if (cancelled) return
          const statusError = isClientError(err)
            ? err
            : new ClientError('parse', 'unexpected status error')
          setState({ phase: 'ready', ready, status: null, statusError })
        }
      } catch (err) {
        if (cancelled) return
        const error = isClientError(err)
          ? err
          : ClientError.network('backend unreachable', err)
        setState({ phase: 'api_unreachable', error })
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  if (state.phase === 'loading') {
    return (
      <section>
        <h2>Status</h2>
        <LoadingBlock label="Checking API and StockBallDB status…" />
      </section>
    )
  }

  if (state.phase === 'api_unreachable') {
    return (
      <section>
        <h2>Status</h2>
        <ErrorBlock
          title="API unreachable"
          message={
            state.error.message ||
            'The FastAPI service did not respond. Start it with: python -m stockballdb.api'
          }
        />
        <InfoBlock
          title="Distinction"
          message="This means the HTTP transport is down. StockBallDB database status cannot be checked until the API is reachable."
        />
      </section>
    )
  }

  const { ready, status, statusError } = state
  const dbUnavailable = status !== null && !status.available

  return (
    <section>
      <h2>Status</h2>

      <div className="card-grid">
        <article className="card">
          <h3>API readiness</h3>
          <p className={ready.ready ? 'ok' : 'bad'}>
            {ready.ready ? 'Reachable' : 'Not ready'}
          </p>
          <dl className="kv">
            <div>
              <dt>Service</dt>
              <dd>{ready.service}</dd>
            </div>
          </dl>
        </article>

        <article className="card">
          <h3>StockBallDB application</h3>
          {statusError ? (
            <ErrorBlock title="Status request failed" message={statusError.message} />
          ) : status === null ? (
            <LoadingBlock />
          ) : dbUnavailable ? (
            <>
              <p className="warn">Unavailable</p>
              <p className="muted">
                API is reachable, but the application reports the database/backend is not
                available.
              </p>
              {status.error_message ? (
                <p className="error-detail">{status.error_message}</p>
              ) : null}
            </>
          ) : (
            <>
              <p className="ok">Available</p>
              <dl className="kv">
                <div>
                  <dt>Database connected</dt>
                  <dd>{status.database_connected ? 'yes' : 'no'}</dd>
                </div>
                <div>
                  <dt>Health</dt>
                  <dd>{status.health_status ?? '—'}</dd>
                </div>
                <div>
                  <dt>Validate V1</dt>
                  <dd>
                    {status.validate_v1_pass === null
                      ? '—'
                      : status.validate_v1_pass
                        ? 'pass'
                        : 'fail'}
                  </dd>
                </div>
                <div>
                  <dt>Alembic head</dt>
                  <dd>
                    <code>{status.alembic_head ?? '—'}</code>
                  </dd>
                </div>
                <div>
                  <dt>Calendar</dt>
                  <dd>{status.calendar_version ?? '—'}</dd>
                </div>
              </dl>
            </>
          )}
        </article>
      </div>
    </section>
  )
}
