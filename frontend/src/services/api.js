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

export default api
