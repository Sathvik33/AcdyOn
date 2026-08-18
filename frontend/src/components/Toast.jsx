import { IconCheck, IconAlert, IconClose } from './Icons.jsx'

const VARIANT_BY_STATUS = {
  SUCCESS: 'success',
  PARTIAL: 'partial',
  FAILED: 'failed',
  RATE_LIMITED: 'rate',
}

export default function ToastStack({ toasts, onDismiss }) {
  if (toasts.length === 0) return null

  return (
    <div className="toast-stack">
      {toasts.map((toast) => {
        const variant = VARIANT_BY_STATUS[toast.status] ?? 'failed'
        return (
          <div className={`toast ${variant}`} key={toast.id} role="status">
            <span className="toast-icon">
              {variant === 'success' ? <IconCheck /> : <IconAlert />}
            </span>
            <div>
              <div className="toast-title">{toast.title}</div>
              <div className="toast-body">{toast.body}</div>
            </div>
            <button className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss">
              <IconClose />
            </button>
          </div>
        )
      })}
    </div>
  )
}
