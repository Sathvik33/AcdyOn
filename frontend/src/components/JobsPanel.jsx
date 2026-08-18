import { IconSearch, IconExternal } from './Icons.jsx'

function initials(company) {
  if (!company) return '—'
  return company
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()
}

function formatDate(iso) {
  if (!iso) return 'Undated'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Undated'
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

function SkeletonRows({ count = 5 }) {
  return Array.from({ length: count }, (_, i) => (
    <div className="skeleton-row" key={i}>
      <div className="skeleton skeleton-avatar" />
      <div style={{ flex: 1 }}>
        <div className="skeleton" style={{ width: '46%', marginBottom: 9 }} />
        <div className="skeleton" style={{ width: '28%', height: 10 }} />
      </div>
    </div>
  ))
}

export default function JobsPanel({
  data,
  loading,
  search,
  onSearchChange,
  page,
  pageSize,
  onPageChange,
}) {
  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">Ingested jobs</div>
          <div className="panel-sub">
            {total} {total === 1 ? 'listing' : 'listings'} stored
          </div>
        </div>
        <div className="panel-tools">
          <label className="search">
            <IconSearch />
            <input
              type="search"
              value={search}
              placeholder="Search title or company"
              onChange={(e) => onSearchChange(e.target.value)}
              aria-label="Search jobs by title or company"
            />
          </label>
        </div>
      </div>

      {loading && items.length === 0 ? (
        <SkeletonRows />
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="empty-title">{search ? 'No matching listings' : 'No listings yet'}</div>
          <div className="empty-sub">
            {search
              ? 'Try a different title or company name.'
              : 'Trigger an ingestion run to pull listings from the source.'}
          </div>
        </div>
      ) : (
        items.map((job) => (
          <article className="job-row" key={job.id}>
            <div className="job-avatar">{initials(job.company)}</div>
            <div className="job-main">
              <div className="job-title" title={job.title || 'Untitled role'}>
                {job.title || 'Untitled role'}
              </div>
              <div className="job-meta">
                <span>{job.company || 'Unknown company'}</span>
                <span className="dot" />
                <span>{job.location || 'Remote'}</span>
                <span className="dot" />
                <span>{formatDate(job.published_at)}</span>
                {job.employment_type ? <span className="tag">{job.employment_type}</span> : null}
              </div>
            </div>
            <div className="job-side">
              <span className="tag">{job.source}</span>
              {job.url ? (
                <a className="job-link" href={job.url} target="_blank" rel="noopener noreferrer">
                  View job
                  <IconExternal />
                </a>
              ) : null}
            </div>
          </article>
        ))
      )}

      {total > pageSize ? (
        <div className="pager">
          <span className="pager-info">
            {from}–{to} of {total}
          </span>
          <div className="pager-buttons">
            <button
              className="btn btn-ghost"
              disabled={page <= 1 || loading}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </button>
            <button
              className="btn btn-ghost"
              disabled={page >= totalPages || loading}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
