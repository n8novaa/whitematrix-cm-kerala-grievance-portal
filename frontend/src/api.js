const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

function errorMessage(data) {
  if (typeof data?.detail === 'string') return data.detail
  if (data && typeof data === 'object') {
    const first = Object.values(data)[0]
    if (Array.isArray(first)) return first.join(' ')
    if (typeof first === 'string') return first
  }
  return 'The request could not be completed.'
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refreshToken')
  if (!refresh) return null
  const response = await fetch(`${API_BASE}/api/v1/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) return null
  const tokens = await response.json()
  localStorage.setItem('accessToken', tokens.access)
  if (tokens.refresh) localStorage.setItem('refreshToken', tokens.refresh)
  return tokens.access
}

export async function api(path, options = {}, retry = true) {
  const token = localStorage.getItem('accessToken')
  const headers = new Headers(options.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE}/api/v1${path}`, { ...options, headers })
  const tokenEndpoint = path.includes('/auth/login/') || path.includes('/auth/refresh/')
  if (response.status === 401 && retry && !tokenEndpoint) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return api(path, options, false)
  }
  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.blob()
  if (!response.ok) throw new ApiError(errorMessage(data), response.status, data)
  return data
}

export function jsonRequest(method, payload) {
  return { method, body: JSON.stringify(payload) }
}
