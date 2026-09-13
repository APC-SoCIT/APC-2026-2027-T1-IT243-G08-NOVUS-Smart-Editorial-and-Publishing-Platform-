import axios from 'axios'

// Development goes through the Vite proxy; production calls Render
// directly, since Vercel serves the frontend from another origin.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
})

// Attach the JWT to every outbound request (Component Diagram: API Service Client)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/**
 * Uploaded files are served by Django. In development the Vite proxy handles
 * /media; in production it must be prefixed with the backend origin.
 */
export function mediaUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_MEDIA_BASE || ''
  return base ? `${base}${path}` : path
}

/**
 * Rewrite relative /media paths to absolute ones.
 *
 * Django returns "/media/…" so the URL works behind the dev proxy. In
 * production the frontend is on Vercel and the files are on Render, so the
 * path must be prefixed. Doing it once here means no component has to know.
 */
const MEDIA_BASE = import.meta.env.VITE_MEDIA_BASE || ''

function absolutiseMedia(value) {
  if (!MEDIA_BASE || value == null) return value
  if (typeof value === 'string') {
    return value.startsWith('/media/') ? MEDIA_BASE + value : value
  }
  if (Array.isArray(value)) return value.map(absolutiseMedia)
  if (typeof value === 'object') {
    const out = {}
    for (const k in value) out[k] = absolutiseMedia(value[k])
    return out
  }
  return value
}

api.interceptors.response.use((response) => {
  response.data = absolutiseMedia(response.data)
  return response
})

/**
 * Transparent token refresh.
 *
 * Access tokens last an hour, so a writer working on a long piece is logged
 * out mid-draft and loses whatever is unsaved. On a 401 we exchange the
 * refresh token once and retry the original request; only if that exchange
 * fails is the session genuinely over.
 *
 * The single-flight guard matters: a dashboard fires several requests at
 * once, and without it an expired token would trigger one refresh per
 * request. With rotation enabled, the first would invalidate the token the
 * others are still using, and they would all fail.
 */
let refreshing = null

function clearSession() {
  localStorage.removeItem('access')
  localStorage.removeItem('refresh')
}

async function refreshAccess() {
  const refresh = localStorage.getItem('refresh')
  if (!refresh) throw new Error('no refresh token')

  // A bare axios call, not `api` — going through the instance would attach
  // the dead access token and recurse into this same interceptor.
  const { data } = await axios.post(
    `${api.defaults.baseURL}/auth/token/refresh/`, { refresh })

  localStorage.setItem('access', data.access)
  if (data.refresh) localStorage.setItem('refresh', data.refresh)
  return data.access
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    // Never retry the refresh endpoint itself, and never retry twice.
    const refreshable =
      status === 401
      && original
      && !original._retried
      && !original.url?.includes('/auth/token/')

    if (!refreshable) return Promise.reject(error)

    original._retried = true

    try {
      refreshing = refreshing || refreshAccess()
      const token = await refreshing
      refreshing = null

      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${token}`
      return api(original)
    } catch (e) {
      refreshing = null
      // The refresh token is spent or expired: the session really is over.
      // Public pages must still work, so clear rather than redirect — a
      // lapsed reader loses their subscriber access, not the magazine.
      clearSession()
      return Promise.reject(error)
    }
  },
)

export default api
