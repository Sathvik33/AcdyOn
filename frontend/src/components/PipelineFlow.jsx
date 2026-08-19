import { Fragment } from 'react'
import {
  IconDownload,
  IconBraces,
  IconLayers,
  IconShield,
  IconCopy,
  IconSave,
} from './Icons.jsx'

const STAGES = [
  { key: 'fetch', name: 'Fetch', icon: <IconDownload /> },
  { key: 'parse', name: 'Parse', icon: <IconBraces /> },
  { key: 'normalize', name: 'Normalize', icon: <IconLayers /> },
  { key: 'validate', name: 'Validate', icon: <IconShield /> },
  { key: 'dedupe', name: 'Deduplicate', icon: <IconCopy /> },
  { key: 'store', name: 'Store', icon: <IconSave /> },
]

function deriveStates(run, isRunning) {
  if (isRunning) return Object.fromEntries(STAGES.map((s) => [s.key, 'active']))
  if (!run) return Object.fromEntries(STAGES.map((s) => [s.key, 'idle']))

  const status = String(run.status || '').toUpperCase()
  const all = (state) => Object.fromEntries(STAGES.map((s) => [s.key, state]))

  if (status === 'RATE_LIMITED') return { ...all('idle'), fetch: 'blocked' }
  if (status === 'FAILED') {
    return run.jobs_found > 0
      ? { ...all('idle'), fetch: 'done', parse: 'failed' }
      : { ...all('idle'), fetch: 'failed' }
  }
  if (status === 'PARTIAL') return { ...all('done'), parse: run.parse_failures > 0 ? 'warn' : 'done' }
  if (status === 'SUCCESS') return all('done')
  return all('idle')
}

function stageNote(key, run) {
  if (!run) return null
  if (key === 'fetch') {
    const httpStr = run.http_status ? ` (HTTP ${run.http_status})` : ''
    const retries = run.retry_count > 0 ? ` · ${run.retry_count} retries` : ''
    return `${run.jobs_found} found${httpStr}${retries}`
  }
  if (key === 'parse' && run.parse_failures > 0) return `${run.parse_failures} failed`
  if (key === 'dedupe') return `${run.duplicate_count ?? run.jobs_skipped} dupes`
  if (key === 'store') return `${run.jobs_inserted} stored`
  return null
}

export default function PipelineFlow({ run, isRunning }) {
  const states = deriveStates(run, isRunning)

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">Ingestion pipeline</div>
          <div className="panel-sub">
            {isRunning
              ? 'Run in progress'
              : run
                ? `Last run ${new Date(run.started_at).toLocaleString()} · ${run.duration_seconds ? `${run.duration_seconds}s` : '0s'}`
                : 'No runs recorded yet'}
          </div>
        </div>
      </div>
      <div className="panel-body">
        <div className="pipeline">
          {STAGES.map((stage, index) => (
            <Fragment key={stage.key}>
              <div className={`stage ${states[stage.key]}`}>
                <div className="stage-node">{stage.icon}</div>
                <div className="stage-name">{stage.name}</div>
                <div className="stage-note">{stageNote(stage.key, run) ?? '\u00a0'}</div>
              </div>
              {index < STAGES.length - 1 ? (
                <div className="stage-link" aria-hidden="true" />
              ) : null}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  )
}
