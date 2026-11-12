import { getAccessToken, getRefreshToken, updateAccessToken, updateRefreshToken } from './auth-storage'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const RETRYABLE_STATUSES = new Set([502, 503, 504])

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms))

async function fetchWithWarmupRetry(url, options) {
  const isReadOnly = ['GET', 'HEAD'].includes((options.method || 'GET').toUpperCase())
  const maxAttempts = isReadOnly ? 3 : 1
  let response

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      response = await fetch(url, options)
    } catch (error) {
      if (attempt === maxAttempts - 1) {
        throw new ApiError('The service is starting or temporarily unreachable. Please try again shortly.', 0, error)
      }
      await wait(1000 * (attempt + 1))
      continue
    }

    if (!isReadOnly || !RETRYABLE_STATUSES.has(response.status) || attempt === maxAttempts - 1) return response
    await wait(1000 * (attempt + 1))
  }

  return response
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
  const refresh = getRefreshToken()
  if (!refresh) return null
  const response = await fetchWithWarmupRetry(`${API_BASE}/api/v1/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) return null
  const tokens = await response.json()
  updateAccessToken(tokens.access)
  if (tokens.refresh) updateRefreshToken(tokens.refresh)
  return tokens.access
}

export async function api(path, options = {}, retry = true) {
  const tokenEndpoint = ['/auth/login/', '/auth/register/', '/auth/refresh/'].some((endpoint) => path.includes(endpoint))
  const token = tokenEndpoint ? null : getAccessToken()
  const headers = new Headers(options.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetchWithWarmupRetry(`${API_BASE}/api/v1${path}`, { ...options, headers })
  if (response.status === 401 && retry && !tokenEndpoint) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      if (path.includes('/auth/logout/') && options.body) {
        const payload = JSON.parse(options.body)
        return api(path, { ...options, body: JSON.stringify({ ...payload, refresh: getRefreshToken() }) }, false)
      }
      return api(path, options, false)
    }
  }
  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.blob()
  if (RETRYABLE_STATUSES.has(response.status)) {
    throw new ApiError('The service is starting or temporarily unavailable. Please try again shortly.', response.status, data)
  }
  if (!response.ok) throw new ApiError(errorMessage(data), response.status, data)
  return data
}

export async function downloadGrievanceAttachment(grievanceId, attachment) {
  const file = await api(`/grievances/${grievanceId}/attachments/${attachment.id}/`)
  const url = URL.createObjectURL(file)
  const link = document.createElement('a')
  link.href = url
  link.download = attachment.original_name
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function jsonRequest(method, payload) {
  return { method, body: JSON.stringify(payload) }
}
