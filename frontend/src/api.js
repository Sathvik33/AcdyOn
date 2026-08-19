const BASE = import.meta.env.DEV ? '' : window.location.origin

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // response had no JSON body; keep the status-based message
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  stats: () => request('/stats'),
  sourceHealth: () => request('/sources/health'),
  runs: (limit = 20) => request(`/ingestion/runs?limit=${limit}`),
  jobs: ({ page = 1, pageSize = 8, search = '', source = '' } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize })
    if (search) params.set('search', search)
    if (source) params.set('source', source)
    return request(`/jobs?${params.toString()}`)
  },
  runIngestion: (source = 'jobicy', allowFallback = true) =>
    request(`/ingestion/run?source=${encodeURIComponent(source)}&allow_fallback=${allowFallback}`, { method: 'POST' }),
}
