import type { ReactNode } from 'react'

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="state-block state-loading" role="status">
      {label}
    </div>
  )
}

export function ErrorBlock({
  title,
  message,
  children,
}: {
  title: string
  message: string
  children?: ReactNode
}) {
  return (
    <div className="state-block state-error" role="alert">
      <strong>{title}</strong>
      <p>{message}</p>
      {children}
    </div>
  )
}

export function InfoBlock({
  title,
  message,
}: {
  title: string
  message: string
}) {
  return (
    <div className="state-block state-info" role="status">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  )
}
