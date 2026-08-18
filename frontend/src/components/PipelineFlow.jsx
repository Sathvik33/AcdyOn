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

// Stage states are derived from the outcome of the most recent run, not from
// per-stage telemetry: the API reports one status plus counters per run.
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
  if (status === 'PARTIAL') return { ...all('done'), validate: 'warn' }
  if (status === 'SUCCESS') return all('done')
  return all('idle')
}

function stageNote(key, run) {
  if (!run) return null
  if (key === 'fetch') return `${run.jobs_found} found`
  if (key === 'dedupe') return `${run.jobs_skipped} skipped`
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
                ? `Last run ${new Date(run.started_at).toLocaleString()}`
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
