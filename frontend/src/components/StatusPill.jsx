const CLASS_BY_STATUS = {
  SUCCESS: 'pill-success',
  PARTIAL: 'pill-partial',
  FAILED: 'pill-failed',
  RATE_LIMITED: 'pill-rate',
  RUNNING: 'pill-idle',
}

export default function StatusPill({ status }) {
  if (!status) return <span className="pill pill-idle">NO RUNS</span>
  const key = String(status).toUpperCase()
  return (
    <span className={`pill ${CLASS_BY_STATUS[key] ?? 'pill-idle'}`}>
      {key.replace('_', ' ')}
    </span>
  )
}
