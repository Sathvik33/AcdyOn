import StatusPill from './StatusPill.jsx'

function formatTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function duration(run) {
  if (!run.started_at || !run.completed_at) return '—'
  const ms = new Date(run.completed_at) - new Date(run.started_at)
  if (!Number.isFinite(ms) || ms < 0) return '—'
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
}

export default function RunHistory({ runs, loading }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">Ingestion history</div>
          <div className="panel-sub">Every run is recorded, including failures</div>
        </div>
      </div>

      {loading && runs.length === 0 ? (
        <div className="panel-body">
          <div className="skeleton" style={{ width: '100%', height: 15, marginBottom: 11 }} />
          <div className="skeleton" style={{ width: '82%', height: 15, marginBottom: 11 }} />
          <div className="skeleton" style={{ width: '64%', height: 15 }} />
        </div>
      ) : runs.length === 0 ? (
        <div className="empty">
          <div className="empty-title">No runs recorded</div>
          <div className="empty-sub">Run the pipeline to populate this history.</div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Source</th>
                <th>Status</th>
                <th>Found</th>
                <th>Inserted</th>
                <th>Skipped</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td className="time">{formatTime(run.started_at)}</td>
                  <td>{run.source}</td>
                  <td>
                    <StatusPill status={run.status} />
                    {run.error_message ? (
                      <div className="error-cell" title={run.error_message}>
                        {run.error_message}
                      </div>
                    ) : null}
                  </td>
                  <td className="num">{run.jobs_found}</td>
                  <td className="num">{run.jobs_inserted}</td>
                  <td className="num">{run.jobs_skipped}</td>
                  <td className="num">{duration(run)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
