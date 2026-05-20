import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// ── Intercepteur requête : injecte le token JWT ────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Intercepteur réponse : gestion du token expiré ────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    // Si 401 et pas déjà en retry → essai de refresh
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return apiClient(original)
        } catch {
          // Refresh échoué → déconnexion
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)
