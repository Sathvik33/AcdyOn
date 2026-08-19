const BASE = import.meta.env.DEV ? '' : window.location.origin

function getUserId() {
  let id = localStorage.getItem('acdyon_user_id')
  if (!id) {
    id = `user_${Math.random().toString(36).substring(2, 10)}`
    localStorage.setItem('acdyon_user_id', id)
  }
  return id
}

async function request(path, options = {}) {
  const headers = {
    'X-User-ID': getUserId(),
    ...(options.headers || {}),
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
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
  getUserId,
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
