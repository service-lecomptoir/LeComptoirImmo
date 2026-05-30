import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// ── Intercepteur requête : injecte le token JWT ───────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('alice_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Intercepteur réponse : redirige vers /login si 401 ───────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('alice_access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
