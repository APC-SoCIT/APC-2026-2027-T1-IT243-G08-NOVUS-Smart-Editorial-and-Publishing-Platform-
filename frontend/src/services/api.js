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

export default api
