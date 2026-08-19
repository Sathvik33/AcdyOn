import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import StatCard from './components/StatCard.jsx'
import StatusPill from './components/StatusPill.jsx'
import PipelineFlow from './components/PipelineFlow.jsx'
import JobsPanel from './components/JobsPanel.jsx'
import RunHistory from './components/RunHistory.jsx'
import ToastStack from './components/Toast.jsx'
import {
  IconLogo,
  IconDatabase,
  IconClock,
  IconPlus,
  IconPulse,
  IconPlay,
  IconRefresh,
  IconAlert,
  IconShield,
} from './components/Icons.jsx'

const PAGE_SIZE = 8

function relativeTime(iso) {
  if (!iso) return 'Never'
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return 'Never'
  const seconds = Math.round((Date.now() - then.getTime()) / 1000)
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return then.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function SourceHealthPill({ state }) {
  const normalized = String(state || 'HEALTHY').toUpperCase()
  let toneClass = 'pill-ok'
  if (normalized === 'DEGRADED') toneClass = 'pill-warn'
  if (normalized === 'BLOCKED' || normalized === 'UNAVAILABLE') toneClass = 'pill-bad'
  return <span className={`pill ${toneClass}`}>{normalized}</span>
}

export default function App() {
  const [stats, setStats] = useState(null)
  const [runs, setRuns] = useState([])
  const [jobs, setJobs] = useState(null)
  const [health, setHealth] = useState(null)
  const [sourceHealthList, setSourceHealthList] = useState([])

  const [loading, setLoading] = useState(true)
  const [jobsLoading, setJobsLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [selectedSource, setSelectedSource] = useState('jobicy')
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)

  const [toasts, setToasts] = useState([])
  const toastId = useRef(0)

  const pushToast = useCallback((toast) => {
    const id = ++toastId.current
    setToasts((current) => [...current, { ...toast, id }])
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 7000)
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const loadOverview = useCallback(async () => {
    try {
      const [statsData, runsData, healthData, sourcesData] = await Promise.all([
        api.stats(),
        api.runs(20),
        api.health(),
        api.sourceHealth(),
      ])
      setStats(statsData)
      setRuns(runsData)
      setHealth(healthData)
      setSourceHealthList(sourcesData)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadJobs = useCallback(async () => {
    setJobsLoading(true)
    try {
      const data = await api.jobs({ page, pageSize: PAGE_SIZE, search: debouncedSearch })
      setJobs(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setJobsLoading(false)
    }
  }, [page, debouncedSearch])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  async function handleRunIngestion() {
    setRunning(true)
    try {
      const result = await api.runIngestion(selectedSource, true)
      const fallbackNote = result.fallback_used ? ' (Circuit breaker fallback activated)' : ''
      pushToast({
        status: result.status,
        title: `Run ${result.status.replace('_', ' ').toLowerCase()}${fallbackNote}`,
        body: `${result.jobs_found} found · ${result.jobs_inserted} inserted · ${result.duplicate_count ?? result.jobs_skipped} dupes · ${result.duration_seconds}s`,
      })
      setPage(1)
      await Promise.all([loadOverview(), loadJobs()])
    } catch (e) {
      pushToast({ status: 'FAILED', title: 'Run failed', body: e.message })
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  async function handleRefresh() {
    await Promise.all([loadOverview(), loadJobs()])
  }

  const latestRun = runs[0] ?? null
  const dbHealthy = health?.database === 'connected'

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <IconLogo />
          </span>
          <div className="brand-text">
            <h1>Job Ingestion Monitor</h1>
            <p>Resilient ingestion with Circuit Breakers & Auto-Fallback</p>
          </div>
        </div>

        <div className="topbar-actions">
          <span className="health">
            <span className={`health-dot ${health ? (dbHealthy ? 'ok' : 'bad') : ''}`} />
            {health ? (dbHealthy ? 'Database connected' : 'Database unreachable') : 'Checking…'}
          </span>
          <select
            className="source-select"
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            disabled={running}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border)',
              background: 'var(--surface-2)',
              color: 'var(--text-1)',
              fontWeight: 500,
            }}
          >
            <option value="jobicy">Jobicy (Primary)</option>
            <option value="remotive">Remotive (Secondary)</option>
            <option value="mock_fallback">Mock Fallback</option>
          </select>
          <button className="btn btn-ghost" onClick={handleRefresh} disabled={loading || running}>
            <IconRefresh />
            Refresh
          </button>
          <button className="btn" onClick={handleRunIngestion} disabled={running}>
            {running ? <span className="spin"><IconRefresh /></span> : <IconPlay />}
            {running ? 'Running…' : 'Run ingestion'}
          </button>
        </div>
      </header>

      {error ? (
        <div className="banner">
          <IconAlert />
          {error}
        </div>
      ) : null}

      <div className="stat-grid">
        <StatCard
          tone="var(--accent)"
          icon={<IconDatabase />}
          label="Total jobs"
          value={stats?.total_jobs ?? '—'}
          footnote="Unique listings stored"
        />
        <StatCard
          tone="var(--cyan)"
          icon={<IconClock />}
          label="Latest ingestion"
          value={relativeTime(stats?.latest_run_at)}
          isText
          footnote={
            stats?.latest_run_at ? new Date(stats.latest_run_at).toLocaleString() : 'No runs yet'
          }
        />
        <StatCard
          tone="var(--green)"
          icon={<IconPlus />}
          label="Jobs added"
          value={stats?.latest_run_inserted ?? 0}
          footnote={`${stats?.latest_run_skipped ?? 0} skipped as duplicates`}
        />
        <StatCard
          tone="var(--violet)"
          icon={<IconPulse />}
          label="Ingestion status"
          value={<StatusPill status={running ? 'RUNNING' : stats?.latest_run_status} />}
          isText
          footnote={running ? 'Pipeline executing' : 'Result of the most recent run'}
        />
      </div>

      {/* Source Health Panel */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <IconShield /> Source Health & Circuit Breakers
            </div>
            <div className="panel-sub">Automatic circuit breakers prevent hammering failing public APIs</div>
          </div>
        </div>
        <div className="panel-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          {sourceHealthList.length === 0 ? (
            <div style={{ color: 'var(--text-3)' }}>Loading source health...</div>
          ) : (
            sourceHealthList.map((sh) => (
              <div
                key={sh.source}
                style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  background: 'var(--surface-1)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ textTransform: 'capitalize' }}>{sh.source}</strong>
                  <SourceHealthPill state={sh.health_state} />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>
                  Failures: {sh.consecutive_failures} · Latency: {sh.last_response_latency ? `${sh.last_response_latency.toFixed(2)}s` : '—'}
                </div>
                {sh.last_http_status ? (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
                    Last HTTP Status: {sh.last_http_status}
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      </section>

      <PipelineFlow run={latestRun} isRunning={running} />

      <JobsPanel
        data={jobs}
        loading={jobsLoading}
        search={search}
        onSearchChange={setSearch}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
      />

      <RunHistory runs={runs} loading={loading} />

      <footer className="foot">
        <span>Sources: Jobicy (Primary), Remotive (Secondary), Mock Fallback</span>
        <span>·</span>
        <a href="/docs" target="_blank" rel="noopener noreferrer">
          API documentation
        </a>
      </footer>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
