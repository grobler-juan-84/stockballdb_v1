import type { ApiErrorBody } from './types'

export type ClientErrorKind = 'network' | 'api' | 'parse'

/** Frontend representation of FastAPI / network failures. */
export class ClientError extends Error {
  readonly kind: ClientErrorKind
  readonly code?: string
  readonly details: Record<string, unknown>
  readonly status?: number

  constructor(
    kind: ClientErrorKind,
    message: string,
    options?: {
      code?: string
      details?: Record<string, unknown>
      status?: number
      cause?: unknown
    },
  ) {
    super(message, options?.cause !== undefined ? { cause: options.cause } : undefined)
    this.name = 'ClientError'
    this.kind = kind
    this.code = options?.code
    this.details = options?.details ?? {}
    this.status = options?.status
  }

  static fromApiBody(status: number, body: ApiErrorBody): ClientError {
    return new ClientError('api', body.message, {
      code: body.code,
      details: body.details ?? {},
      status,
    })
  }

  static network(message = 'backend unreachable', cause?: unknown): ClientError {
    return new ClientError('network', message, { cause })
  }

  get isNetworkFailure(): boolean {
    return this.kind === 'network'
  }
}

export function isClientError(value: unknown): value is ClientError {
  return value instanceof ClientError
}
