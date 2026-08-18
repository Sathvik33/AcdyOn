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

export default function App() {
  const [stats, setStats] = useState(null)
  const [runs, setRuns] = useState([])
  const [jobs, setJobs] = useState(null)
  const [health, setHealth] = useState(null)

  const [loading, setLoading] = useState(true)
  const [jobsLoading, setJobsLoading] = useState(true)
  const [running, setRunning] = useState(false)
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
      const [statsData, runsData, healthData] = await Promise.all([
        api.stats(),
        api.runs(20),
        api.health(),
      ])
      setStats(statsData)
      setRuns(runsData)
      setHealth(healthData)
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
      const result = await api.runIngestion()
      pushToast({
        status: result.status,
        title: `Run ${result.status.replace('_', ' ').toLowerCase()}`,
        body: `${result.jobs_found} found · ${result.jobs_inserted} inserted · ${result.jobs_skipped} skipped`,
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
            <p>Resilient ingestion from public job sources</p>
          </div>
        </div>

        <div className="topbar-actions">
          <span className="health">
            <span className={`health-dot ${health ? (dbHealthy ? 'ok' : 'bad') : ''}`} />
            {health ? (dbHealthy ? 'Database connected' : 'Database unreachable') : 'Checking…'}
          </span>
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
        <span>Source: Jobicy public jobs API</span>
        <span>·</span>
        <a href="/docs" target="_blank" rel="noopener noreferrer">
          API documentation
        </a>
      </footer>

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
